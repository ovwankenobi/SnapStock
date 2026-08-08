import uuid
from datetime import date

from app.schemas.base import CamelModel


class AnalyticsSummary(CamelModel):
    today_sale_count: int
    today_revenue_cents: int
    low_stock_count: int
    week_over_week_revenue_change_pct: float | None


class TopProduct(CamelModel):
    product_id: uuid.UUID
    product_name: str
    quantity_sold: int
    revenue_cents: int


class SalesTrendPoint(CamelModel):
    date: date
    sale_count: int
    revenue_cents: int


class ProductForecast(CamelModel):
    product_id: uuid.UUID
    product_name: str
    stock_pieces: int
    avg_daily_pieces_week: float | None
    avg_daily_pieces_month: float | None
    days_of_stock_remaining: float | None
    at_risk: bool
    is_estimate: bool = True
