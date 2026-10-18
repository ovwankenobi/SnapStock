import uuid
from datetime import date

from pydantic import field_validator
from pydantic.alias_generators import to_camel

from app.models.product import UnitType
from app.schemas.base import CamelModel


class AnalyticsSummary(CamelModel):
    today_sale_count: int
    today_revenue_cents: int
    low_stock_count: int
    week_over_week_revenue_change_pct: float | None


class PeriodMetrics(CamelModel):
    # gross (at list price) - price adjustments - discounts - refunds == net
    gross_sales_cents: int
    price_adjustments_cents: int
    discounts_cents: int
    refunds_cents: int
    net_sales_cents: int
    transactions: int
    units_sold: float
    avg_transaction_cents: int | None
    cogs_cents: int
    gross_profit_cents: int | None
    gross_margin_pct: float | None
    cost_coverage_pct: float | None


class OverviewChange(CamelModel):
    net_sales_cents: float | None
    transactions: float | None
    units_sold: float | None
    avg_transaction_cents: float | None
    gross_profit_cents: float | None


class AnalyticsOverview(CamelModel):
    start: date
    end: date
    previous_start: date
    previous_end: date
    current: PeriodMetrics
    previous: PeriodMetrics
    change_pct: OverviewChange


class TopProduct(CamelModel):
    product_id: uuid.UUID
    product_name: str
    unit_type: UnitType
    unit_label: str | None = None
    quantity_sold: int
    revenue_cents: int
    gross_profit_cents: int | None = None
    margin_pct: float | None = None


class SalesTrendPoint(CamelModel):
    date: date
    sale_count: int
    revenue_cents: int
    gross_profit_cents: int | None = None


class WeekdayPattern(CamelModel):
    weekday: int  # Monday=0
    avg_revenue_cents: int
    avg_transactions: float


class HourPattern(CamelModel):
    hour: int
    avg_revenue_cents: int
    avg_transactions: float


class SalesPatterns(CamelModel):
    start: date
    end: date
    weekdays: list[WeekdayPattern]
    hours: list[HourPattern]


class InventoryHealthItem(CamelModel):
    product_id: uuid.UUID
    product_name: str
    unit_type: UnitType
    unit_label: str | None = None
    pieces_per_unit: int
    stock_pieces: int
    low_stock_threshold: int
    avg_daily_7: float | None
    avg_daily_30: float | None
    daily_rate: float | None
    days_remaining: float | None
    suggested_reorder_pieces: int
    turnover_30: float | None
    stock_value_cents: int | None
    last_sold_on: date | None
    status: str  # out_of_stock | stockout_risk | low | slow_moving | overstocked | healthy


class ProductForecast(CamelModel):
    product_id: uuid.UUID
    product_name: str
    unit_type: UnitType
    unit_label: str | None = None
    pieces_per_unit: int
    stock_pieces: int
    method: str  # history | fallback | none
    confidence: str  # high | medium | low
    history_days: int
    daily_rate: float | None
    forecast_7: float | None
    forecast_14: float | None
    avg_daily_pieces_week: float | None
    avg_daily_pieces_month: float | None
    days_of_stock_remaining: float | None
    at_risk: bool
    is_estimate: bool = True


class ForecastResponse(CamelModel):
    # 100 - WAPE% of last week's forecast vs what actually sold; None until there is data to score.
    accuracy_pct: float | None
    weekday_adjusted: bool
    weekday_factors: list[float] | None
    items: list[ProductForecast]


class Insight(CamelModel):
    code: str
    severity: str  # high | medium | low
    action: str
    params: dict[str, str | int | float | None]
    product_id: uuid.UUID | None = None

    # A free-form dict that CamelModel can't alias, so its keys are camelCased here to match the wire format.
    @field_validator("params")
    @classmethod
    def camel_case_keys(cls, params: dict) -> dict:
        return {to_camel(key): value for key, value in params.items()}
