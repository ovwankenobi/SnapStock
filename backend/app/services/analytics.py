import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import Date, cast, func
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.sale import Sale, SaleItem

RANGE_DAYS = {"today": 1, "week": 7, "month": 30}
MIN_HISTORY_DAYS = 14


def _range_start(range_key: str | None) -> datetime:
    now = datetime.now(timezone.utc)
    if range_key == "today":
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    days = RANGE_DAYS.get(range_key or "week", 7)
    return now - timedelta(days=days)


def get_summary(db: Session, seller_id: uuid.UUID) -> dict:
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)
    two_weeks_start = now - timedelta(days=14)

    today_count, today_revenue = db.query(
        func.count(Sale.id), func.coalesce(func.sum(Sale.total_cents), 0)
    ).filter(Sale.seller_id == seller_id, Sale.created_at >= today_start).one()

    this_week_revenue = (
        db.query(func.coalesce(func.sum(Sale.total_cents), 0))
        .filter(Sale.seller_id == seller_id, Sale.created_at >= week_start)
        .scalar()
    )
    last_week_revenue = (
        db.query(func.coalesce(func.sum(Sale.total_cents), 0))
        .filter(
            Sale.seller_id == seller_id,
            Sale.created_at >= two_weeks_start,
            Sale.created_at < week_start,
        )
        .scalar()
    )

    change_pct = None
    if last_week_revenue:
        change_pct = round((this_week_revenue - last_week_revenue) / last_week_revenue * 100, 1)

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
        "today_sale_count": today_count,
        "today_revenue_cents": today_revenue,
        "low_stock_count": low_stock_count,
        "week_over_week_revenue_change_pct": change_pct,
    }


def get_top_products(db: Session, seller_id: uuid.UUID, range_key: str | None, limit: int) -> list[dict]:
    start = _range_start(range_key)
    rows = (
        db.query(
            SaleItem.product_id,
            func.max(SaleItem.product_name_snapshot).label("product_name"),
            func.sum(SaleItem.quantity).label("quantity_sold"),
            func.sum(SaleItem.line_total_cents).label("revenue_cents"),
        )
        .join(Sale, Sale.id == SaleItem.sale_id)
        .filter(Sale.seller_id == seller_id, Sale.created_at >= start, SaleItem.product_id.isnot(None))
        .group_by(SaleItem.product_id)
        .order_by(func.sum(SaleItem.line_total_cents).desc())
        .limit(limit)
        .all()
    )
    return [
        {
            "product_id": row.product_id,
            "product_name": row.product_name,
            "quantity_sold": row.quantity_sold,
            "revenue_cents": row.revenue_cents,
        }
        for row in rows
    ]


def get_sales_trend(db: Session, seller_id: uuid.UUID, range_key: str | None) -> list[dict]:
    start = _range_start(range_key)
    day_expr = cast(Sale.created_at, Date)

    rows = (
        db.query(
            day_expr.label("day"),
            func.count(Sale.id).label("sale_count"),
            func.coalesce(func.sum(Sale.total_cents), 0).label("revenue_cents"),
        )
        .filter(Sale.seller_id == seller_id, Sale.created_at >= start)
        .group_by(day_expr)
        .all()
    )
    by_day = {row.day: row for row in rows}

    span_days = RANGE_DAYS.get(range_key or "week", 7)
    today = datetime.now(timezone.utc).date()
    points = []
    for offset in range(span_days - 1, -1, -1):
        day = today - timedelta(days=offset)
        row = by_day.get(day)
        points.append(
            {
                "date": day,
                "sale_count": row.sale_count if row else 0,
                "revenue_cents": row.revenue_cents if row else 0,
            }
        )
    return points


def get_forecast(db: Session, seller_id: uuid.UUID) -> list[dict]:
    now = datetime.now(timezone.utc)
    cutoff_7 = now - timedelta(days=7)
    cutoff_30 = now - timedelta(days=30)

    history_days_expr = func.count(func.distinct(cast(Sale.created_at, Date))).filter(
        Sale.created_at >= cutoff_30
    )
    pieces_7d_expr = func.coalesce(
        func.sum(SaleItem.pieces_deducted).filter(Sale.created_at >= cutoff_7), 0
    )
    pieces_30d_expr = func.coalesce(
        func.sum(SaleItem.pieces_deducted).filter(Sale.created_at >= cutoff_30), 0
    )

    rows = (
        db.query(
            Product.id,
            Product.name,
            Product.stock_pieces,
            history_days_expr.label("history_days"),
            pieces_7d_expr.label("pieces_7d"),
            pieces_30d_expr.label("pieces_30d"),
        )
        .outerjoin(SaleItem, SaleItem.product_id == Product.id)
        .outerjoin(Sale, Sale.id == SaleItem.sale_id)
        .filter(Product.seller_id == seller_id, Product.is_active.is_(True))
        .group_by(Product.id, Product.name, Product.stock_pieces)
        .order_by(Product.name)
        .all()
    )

    forecasts = []
    for row in rows:
        has_history = row.history_days >= MIN_HISTORY_DAYS
        avg_week = (row.pieces_7d / 7) if has_history else None
        avg_month = (row.pieces_30d / 30) if has_history else None
        days_remaining = row.stock_pieces / avg_week if has_history and avg_week else None
        at_risk = days_remaining is not None and days_remaining <= 7

        forecasts.append(
            {
                "product_id": row.id,
                "product_name": row.name,
                "stock_pieces": row.stock_pieces,
                "avg_daily_pieces_week": avg_week,
                "avg_daily_pieces_month": avg_month,
                "days_of_stock_remaining": days_remaining,
                "at_risk": at_risk,
            }
        )
    return forecasts
