"""Core sales and profitability analytics (P1 + P2).

Status rules, shared by every metric here:
- voided sales were mistakes and are invisible;
- refunded sales count in gross sales and come back out as `refunds`;
- net sales, transactions, units and profit come from completed sales only.

Walk-in and itemized sales are aggregated identically.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta

from sqlalchemy import BigInteger, Float, case, cast, func
from sqlalchemy.orm import Session

from app.core.business_time import (
    DateRange,
    local_day_expr,
    local_hour_expr,
    local_weekday_expr,
    trailing_days,
)
from app.models.product import Product, UnitType
from app.models.sale import Sale, SaleItem, SaleStatus

GRANULARITIES = ("day", "week", "month")


def _quantity_scale():
    return case((SaleItem.unit_type_snapshot == UnitType.MEASURE, 1000), else_=1)


def _list_line_total():
    """SQL mirror of inventory.line_total_cents at the list (pre-edit) price."""
    scale = _quantity_scale()
    return (cast(SaleItem.quantity, BigInteger) * SaleItem.list_price_cents_snapshot * 2 + scale) / (2 * scale)


@dataclass
class SaleRow:
    status: SaleStatus
    local_day: date
    hour: int
    weekday: int
    subtotal_cents: int
    discount_cents: int
    total_cents: int
    line_total_cents: int
    list_total_cents: int
    costed_line_cents: int
    cogs_cents: int
    units: float

    @property
    def price_adjustment_cents(self) -> int:
        return self.list_total_cents - self.line_total_cents

    @property
    def costed_net_cents(self) -> float:
        """Revenue on lines with a known cost, after this sale's share of the sale-level discount."""
        if not self.subtotal_cents:
            return 0
        return self.costed_line_cents - self.discount_cents * self.costed_line_cents / self.subtotal_cents


def sale_rows(db: Session, seller_id: uuid.UUID, start_utc: datetime, end_utc: datetime) -> list[SaleRow]:
    """One row per completed or refunded sale in `[start_utc, end_utc)`, with its line aggregates."""
    items = (
        db.query(
            SaleItem.sale_id.label("sale_id"),
            func.sum(SaleItem.line_total_cents).label("line_total"),
            func.sum(_list_line_total()).label("list_total"),
            func.sum(case((SaleItem.cost_total_cents.isnot(None), SaleItem.line_total_cents), else_=0)).label(
                "costed_line"
            ),
            func.sum(func.coalesce(SaleItem.cost_total_cents, 0)).label("cogs"),
            func.sum(cast(SaleItem.quantity, Float) / _quantity_scale()).label("units"),
        )
        .group_by(SaleItem.sale_id)
        .subquery()
    )
    rows = (
        db.query(
            Sale.status,
            local_day_expr(Sale.created_at).label("day"),
            local_hour_expr(Sale.created_at).label("hour"),
            local_weekday_expr(Sale.created_at).label("weekday"),
            Sale.subtotal_cents,
            Sale.discount_cents,
            Sale.total_cents,
            items.c.line_total,
            items.c.list_total,
            items.c.costed_line,
            items.c.cogs,
            items.c.units,
        )
        .outerjoin(items, items.c.sale_id == Sale.id)
        .filter(
            Sale.seller_id == seller_id,
            Sale.status.in_((SaleStatus.COMPLETED, SaleStatus.REFUNDED)),
            Sale.created_at >= start_utc,
            Sale.created_at < end_utc,
        )
        .all()
    )
    return [
        SaleRow(
            status=row.status,
            local_day=row.day,
            hour=row.hour,
            weekday=row.weekday,
            subtotal_cents=row.subtotal_cents,
            discount_cents=row.discount_cents,
            total_cents=row.total_cents,
            line_total_cents=int(row.line_total or 0),
            list_total_cents=int(row.list_total or 0),
            costed_line_cents=int(row.costed_line or 0),
            cogs_cents=int(row.cogs or 0),
            units=float(row.units or 0),
        )
        for row in rows
    ]


@dataclass
class PeriodMetrics:
    gross_sales_cents: int = 0
    price_adjustments_cents: int = 0
    discounts_cents: int = 0
    refunds_cents: int = 0
    net_sales_cents: int = 0
    transactions: int = 0
    units_sold: float = 0
    cogs_cents: int = 0
    costed_net: float = field(default=0, repr=False)

    @property
    def avg_transaction_cents(self) -> int | None:
        return round(self.net_sales_cents / self.transactions) if self.transactions else None

    @property
    def gross_profit_cents(self) -> int | None:
        """Profit on the sales whose cost is known. None until any cost is recorded."""
        if not self.costed_net:
            return None
        return round(self.costed_net - self.cogs_cents)

    @property
    def gross_margin_pct(self) -> float | None:
        if not self.costed_net:
            return None
        return round((self.costed_net - self.cogs_cents) / self.costed_net * 100, 1)

    @property
    def cost_coverage_pct(self) -> float | None:
        """Share of net sales whose cost is known, so a margin from partial data reads as partial."""
        if not self.net_sales_cents:
            return None
        return round(min(100.0, self.costed_net / self.net_sales_cents * 100), 1)

    def to_dict(self) -> dict:
        return {
            "gross_sales_cents": self.gross_sales_cents,
            "price_adjustments_cents": self.price_adjustments_cents,
            "discounts_cents": self.discounts_cents,
            "refunds_cents": self.refunds_cents,
            "net_sales_cents": self.net_sales_cents,
            "transactions": self.transactions,
            "units_sold": round(self.units_sold, 3),
            "avg_transaction_cents": self.avg_transaction_cents,
            "cogs_cents": self.cogs_cents,
            "gross_profit_cents": self.gross_profit_cents,
            "gross_margin_pct": self.gross_margin_pct,
            "cost_coverage_pct": self.cost_coverage_pct,
        }


def aggregate(rows: list[SaleRow]) -> PeriodMetrics:
    """gross - price adjustments - discounts - refunds == net."""
    m = PeriodMetrics()
    for row in rows:
        m.gross_sales_cents += row.subtotal_cents + row.price_adjustment_cents
        m.price_adjustments_cents += row.price_adjustment_cents
        m.discounts_cents += row.discount_cents
        if row.status == SaleStatus.REFUNDED:
            m.refunds_cents += row.total_cents
            continue
        m.net_sales_cents += row.total_cents
        m.transactions += 1
        m.units_sold += row.units
        m.cogs_cents += row.cogs_cents
        m.costed_net += row.costed_net_cents
    return m


def period_metrics(db: Session, seller_id: uuid.UUID, period: DateRange) -> PeriodMetrics:
    return aggregate(sale_rows(db, seller_id, period.start_utc, period.end_utc))


def get_summary(db: Session, seller_id: uuid.UUID) -> dict:
    today = period_metrics(db, seller_id, trailing_days(1))
    this_week_range = trailing_days(7)
    this_week = period_metrics(db, seller_id, this_week_range).net_sales_cents
    last_week = period_metrics(db, seller_id, this_week_range.previous()).net_sales_cents

    change_pct = None
    if last_week:
        change_pct = round((this_week - last_week) / last_week * 100, 1)

    low_stock_count = (
        db.query(func.count(Product.id))
        .filter(
            Product.seller_id == seller_id,
            Product.is_active.is_(True),
            Product.stock_pieces <= Product.low_stock_threshold,
        )
        .scalar()
    )

    return {
        "today_sale_count": today.transactions,
        "today_revenue_cents": today.net_sales_cents,
        "low_stock_count": low_stock_count,
        "week_over_week_revenue_change_pct": change_pct,
    }


def _change_pct(current: float | None, previous: float | None) -> float | None:
    if current is None or not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def get_overview(db: Session, seller_id: uuid.UUID, period: DateRange) -> dict:
    current = period_metrics(db, seller_id, period).to_dict()
    previous_range = period.previous()
    previous = period_metrics(db, seller_id, previous_range).to_dict()
    return {
        "start": period.start,
        "end": period.end,
        "previous_start": previous_range.start,
        "previous_end": previous_range.end,
        "current": current,
        "previous": previous,
        "change_pct": {
            key: _change_pct(current[key], previous[key])
            for key in ("net_sales_cents", "transactions", "units_sold", "avg_transaction_cents", "gross_profit_cents")
        },
    }


def _bucket(day: date, granularity: str) -> date:
    if granularity == "week":
        return day - timedelta(days=day.weekday())
    if granularity == "month":
        return day.replace(day=1)
    return day


def get_sales_trend(db: Session, seller_id: uuid.UUID, period: DateRange, granularity: str = "day") -> list[dict]:
    """Net sales per local day/week/month bucket, zero-filled so gaps stay visible."""
    buckets: dict[date, list[SaleRow]] = {}
    for day in period.each_day():
        buckets.setdefault(_bucket(day, granularity), [])
    for row in sale_rows(db, seller_id, period.start_utc, period.end_utc):
        buckets.setdefault(_bucket(row.local_day, granularity), []).append(row)

    points = []
    for bucket_start in sorted(buckets):
        m = aggregate(buckets[bucket_start])
        points.append(
            {
                "date": bucket_start,
                "sale_count": m.transactions,
                "revenue_cents": m.net_sales_cents,
                "gross_profit_cents": m.gross_profit_cents,
            }
        )
    return points


def get_top_products(
    db: Session, seller_id: uuid.UUID, period: DateRange, limit: int, sort: str = "revenue"
) -> list[dict]:
    """Best sellers among completed sales. Profit is per line, before sale-level discounts."""
    costed_revenue = func.sum(case((SaleItem.cost_total_cents.isnot(None), SaleItem.line_total_cents), else_=0))
    cogs = func.sum(SaleItem.cost_total_cents)
    profit = costed_revenue - func.coalesce(cogs, 0)
    order_by = {
        "revenue": func.sum(SaleItem.line_total_cents),
        "quantity": func.sum(cast(SaleItem.quantity, Float) / _quantity_scale()),
        "profit": case((cogs.is_(None), None), else_=profit),
    }[sort]

    rows = (
        db.query(
            SaleItem.product_id,
            func.max(SaleItem.product_name_snapshot).label("product_name"),
            func.max(SaleItem.unit_type_snapshot).label("unit_type"),
            func.max(SaleItem.unit_label_snapshot).label("unit_label"),
            func.sum(SaleItem.quantity).label("quantity_sold"),
            func.sum(SaleItem.line_total_cents).label("revenue_cents"),
            costed_revenue.label("costed_revenue"),
            cogs.label("cogs"),
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(
            Sale.seller_id == seller_id,
            Sale.status == SaleStatus.COMPLETED,
            Sale.created_at >= period.start_utc,
            Sale.created_at < period.end_utc,
            SaleItem.product_id.isnot(None),
        )
        .group_by(SaleItem.product_id)
        .order_by(order_by.desc().nulls_last(), func.sum(SaleItem.line_total_cents).desc())
        .limit(limit)
        .all()
    )
    result = []
    for row in rows:
        has_cost = row.cogs is not None and row.costed_revenue
        gross_profit = int(row.costed_revenue - row.cogs) if has_cost else None
        result.append(
            {
                "product_id": row.product_id,
                "product_name": row.product_name,
                "unit_type": row.unit_type,
                "unit_label": row.unit_label,
                "quantity_sold": row.quantity_sold,
                "revenue_cents": row.revenue_cents,
                "gross_profit_cents": gross_profit,
                "margin_pct": round(gross_profit / row.costed_revenue * 100, 1) if has_cost else None,
            }
        )
    return result


def get_patterns(db: Session, seller_id: uuid.UUID, weeks: int) -> dict:
    """Average net sales and transactions per local weekday and per local hour of day."""
    period = trailing_days(weeks * 7)
    rows = [r for r in sale_rows(db, seller_id, period.start_utc, period.end_utc) if r.status == SaleStatus.COMPLETED]

    # Each weekday occurs `weeks` times in the window; each hour occurs once per day.
    weekday_counts = [0] * 7
    for day in period.each_day():
        weekday_counts[day.weekday()] += 1
    by_weekday = [{"revenue": 0, "count": 0} for _ in range(7)]
    by_hour = [{"revenue": 0, "count": 0} for _ in range(24)]
    for row in rows:
        by_weekday[row.weekday]["revenue"] += row.total_cents
        by_weekday[row.weekday]["count"] += 1
        by_hour[row.hour]["revenue"] += row.total_cents
        by_hour[row.hour]["count"] += 1

    return {
        "start": period.start,
        "end": period.end,
        "weekdays": [
            {
                "weekday": w,
                "avg_revenue_cents": round(by_weekday[w]["revenue"] / weekday_counts[w]) if weekday_counts[w] else 0,
                "avg_transactions": round(by_weekday[w]["count"] / weekday_counts[w], 2) if weekday_counts[w] else 0,
            }
            for w in range(7)
        ],
        "hours": [
            {
                "hour": h,
                "avg_revenue_cents": round(by_hour[h]["revenue"] / period.days),
                "avg_transactions": round(by_hour[h]["count"] / period.days, 2),
            }
            for h in range(24)
        ],
    }

