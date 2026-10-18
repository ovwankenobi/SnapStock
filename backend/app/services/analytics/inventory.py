"""Inventory intelligence (P3) and the per-product demand data shared with forecasting.

Demand counts completed sales only: voided and refunded sales gave their stock back.
All quantities are stock pieces (thousandths for measure products), the same unit
as `Product.stock_pieces` and the restock endpoints.
"""

import math
import uuid
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.business_time import BUSINESS_TZ, local_day_expr, local_today
from app.models.product import Product
from app.models.sale import Sale, SaleItem, SaleStatus
from app.services.analytics import forecast as fc
from app.services.inventory import quantity_scale

HISTORY_DAYS = 60
STOCKOUT_RISK_DAYS = 7
OVERSTOCK_DAYS = 60
SLOW_MOVING_DAYS = 14
SAFETY_STOCK_DAYS = 3
REORDER_HORIZON_DAYS = 14


@dataclass
class ProductDemand:
    product: Product
    series: dict[date, float]
    first_sale: date | None
    last_sale: date | None
    estimate: fc.DemandEstimate
    forecast7: float | None
    forecast14: float | None
    days_remaining: float | None
    revenue30_cents: int
    pieces30: float

    @property
    def unit_divisor(self) -> int:
        """Stock pieces per selling unit, e.g. 12 for a dozen-bundle, 1000 for a kg measure."""
        return self.product.pieces_per_unit * quantity_scale(self.product.unit_type)

    @property
    def suggested_reorder_pieces(self) -> int:
        """Enough for the next 14 days plus 3 days of safety stock, rounded up to whole selling units."""
        if self.forecast14 is None:
            return 0
        safety = SAFETY_STOCK_DAYS * (self.estimate.avg_daily_month or self.estimate.daily_rate or 0)
        needed = self.forecast14 + safety - self.product.stock_pieces
        if needed <= 0:
            return 0
        step = self.product.pieces_per_unit
        return math.ceil(needed / step) * step

    @property
    def stock_value_cents(self) -> int | None:
        if self.product.cost_cents is None:
            return None
        return round(self.product.cost_cents * self.product.stock_pieces / self.unit_divisor)

    @property
    def turnover30(self) -> float | None:
        if self.product.stock_pieces <= 0:
            return None
        return round(self.pieces30 / self.product.stock_pieces, 2)

    @property
    def status(self) -> str:
        today = local_today()
        stock = self.product.stock_pieces
        if stock <= 0:
            return "out_of_stock"
        if self.days_remaining is not None and self.days_remaining <= STOCKOUT_RISK_DAYS:
            return "stockout_risk"
        if stock <= self.product.low_stock_threshold:
            return "low"
        since = self.last_sale or self.product.created_at.astimezone(BUSINESS_TZ).date()
        if (today - since).days >= SLOW_MOVING_DAYS:
            return "slow_moving"
        if self.days_remaining is not None and self.days_remaining > OVERSTOCK_DAYS:
            return "overstocked"
        return "healthy"


@dataclass
class ShopDemand:
    products: list[ProductDemand]
    shop_daily: dict[date, float]
    shop_first_sale: date | None
    factors: list[float] | None


def load_demand(db: Session, seller_id: uuid.UUID) -> ShopDemand:
    today = local_today()
    since = today - timedelta(days=HISTORY_DAYS - 1)
    day = local_day_expr(Sale.created_at)
    completed = (Sale.seller_id == seller_id, Sale.status == SaleStatus.COMPLETED)

    products = (
        db.query(Product)
        .filter(Product.seller_id == seller_id, Product.is_active.is_(True))
        .order_by(Product.name)
        .all()
    )

    series: dict[uuid.UUID, dict[date, float]] = {}
    revenue30: dict[uuid.UUID, int] = {}
    cutoff30 = today - timedelta(days=29)
    for row in (
        db.query(
            SaleItem.product_id,
            day.label("day"),
            func.sum(SaleItem.pieces_deducted).label("pieces"),
            func.sum(SaleItem.line_total_cents).label("revenue"),
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(*completed, SaleItem.product_id.isnot(None), day >= since)
        .group_by(SaleItem.product_id, day)
        .all()
    ):
        series.setdefault(row.product_id, {})[row.day] = float(row.pieces)
        if row.day >= cutoff30:
            revenue30[row.product_id] = revenue30.get(row.product_id, 0) + int(row.revenue)

    bounds = {
        row.product_id: (row.first, row.last)
        for row in db.query(SaleItem.product_id, func.min(day).label("first"), func.max(day).label("last"))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(*completed, SaleItem.product_id.isnot(None))
        .group_by(SaleItem.product_id)
        .all()
    }

    # The shop's weekday rhythm uses net sales, which (unlike pieces) is comparable across products.
    shop_daily = {
        row.day: float(row.revenue)
        for row in db.query(day.label("day"), func.sum(Sale.total_cents).label("revenue"))
        .filter(*completed, day >= since)
        .group_by(day)
        .all()
    }
    shop_first_sale = db.query(func.min(day)).filter(*completed).scalar()
    factors = fc.weekday_factors(shop_daily, today, shop_first_sale)
    tomorrow = today + timedelta(days=1)

    demand = []
    for product in products:
        product_series = series.get(product.id, {})
        first_sale, last_sale = bounds.get(product.id, (None, None))
        estimate = fc.estimate_demand(product_series, today, first_sale)
        demand.append(
            ProductDemand(
                product=product,
                series=product_series,
                first_sale=first_sale,
                last_sale=last_sale,
                estimate=estimate,
                forecast7=fc.forecast_total(estimate.daily_rate, tomorrow, 7, factors),
                forecast14=fc.forecast_total(estimate.daily_rate, tomorrow, 14, factors),
                days_remaining=fc.days_of_stock(product.stock_pieces, estimate.daily_rate),
                revenue30_cents=revenue30.get(product.id, 0),
                pieces30=fc.window_sum(product_series, today, 30),
            )
        )
    return ShopDemand(demand, shop_daily, shop_first_sale, factors)


STATUS_ORDER = ["out_of_stock", "stockout_risk", "low", "slow_moving", "overstocked", "healthy"]


def get_inventory_health(db: Session, seller_id: uuid.UUID) -> list[dict]:
    shop = load_demand(db, seller_id)
    rows = [
        {
            "product_id": d.product.id,
            "product_name": d.product.name,
            "unit_type": d.product.unit_type,
            "unit_label": d.product.unit_label,
            "pieces_per_unit": d.product.pieces_per_unit,
            "stock_pieces": d.product.stock_pieces,
            "low_stock_threshold": d.product.low_stock_threshold,
            "avg_daily_7": d.estimate.avg_daily_week,
            "avg_daily_30": d.estimate.avg_daily_month,
            "daily_rate": d.estimate.daily_rate,
            "days_remaining": d.days_remaining,
            "suggested_reorder_pieces": d.suggested_reorder_pieces,
            "turnover_30": d.turnover30,
            "stock_value_cents": d.stock_value_cents,
            "last_sold_on": d.last_sale,
            "status": d.status,
        }
        for d in shop.products
    ]
    rows.sort(
        key=lambda r: (
            STATUS_ORDER.index(r["status"]),
            math.inf if r["days_remaining"] is None else r["days_remaining"],
        )
    )
    return rows


def get_forecast(db: Session, seller_id: uuid.UUID) -> dict:
    shop = load_demand(db, seller_id)
    accuracy = fc.backtest_accuracy(
        {d.product.id: d.series for d in shop.products},
        {d.product.id: d.first_sale for d in shop.products if d.first_sale},
        shop.shop_daily,
        shop.shop_first_sale,
        local_today(),
    )
    items = [
        {
            "product_id": d.product.id,
            "product_name": d.product.name,
            "unit_type": d.product.unit_type,
            "unit_label": d.product.unit_label,
            "pieces_per_unit": d.product.pieces_per_unit,
            "stock_pieces": d.product.stock_pieces,
            "method": d.estimate.method,
            "confidence": d.estimate.confidence,
            "history_days": d.estimate.history_days,
            "daily_rate": d.estimate.daily_rate,
            "forecast_7": d.forecast7,
            "forecast_14": d.forecast14,
            # Kept from the original forecast: only set when the product has its own history.
            "avg_daily_pieces_week": d.estimate.avg_daily_week,
            "avg_daily_pieces_month": d.estimate.avg_daily_month,
            "days_of_stock_remaining": d.days_remaining,
            "at_risk": d.days_remaining is not None and d.days_remaining <= STOCKOUT_RISK_DAYS,
        }
        for d in shop.products
    ]
    items.sort(key=lambda r: math.inf if r["days_of_stock_remaining"] is None else r["days_of_stock_remaining"])
    return {
        "accuracy_pct": accuracy,
        "weekday_adjusted": shop.factors is not None,
        "weekday_factors": shop.factors,
        "items": items,
    }
