"""Rule-based business insights (P5).

Each insight is `{code, severity, params, product_id, action}`. `code`/`action`
are stable keys the frontend translates; `params` carries the figures behind the
insight so the seller can see why it fired. Every rule has a minimum volume so
small numbers don't produce noise.
"""

import uuid
from datetime import timedelta

from sqlalchemy.orm import Session

from app.core.business_time import DateRange, local_today, trailing_days
from app.services.analytics.inventory import ProductDemand, load_demand
from app.services.analytics.sales import period_metrics

SALES_SWING_PCT = 30
SALES_SWING_MIN_AVG_CENTS = 50_000
LOW_MARGIN_PCT = 10
LOW_MARGIN_MIN_REVENUE_CENTS = 100_000
MISSING_COST_REVENUE_SHARE = 0.2
BESTSELLER_GROWTH = 2.0
BESTSELLER_MIN_UNITS = 10
STOCKOUT_DAYS = 3
OVERSTOCK_DAYS = 60
OVERSTOCK_MIN_VALUE_CENTS = 100_000
MAX_INSIGHTS = 20
# Per rule, so one noisy rule (say, a shop full of slow stock) can't crowd out the rest.
MAX_PER_CODE = 3

SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


def _insight(code, severity, action, params, product: ProductDemand | None = None) -> dict:
    if product is not None:
        params = {"product": product.product.name, **params}
    return {
        "code": code,
        "severity": severity,
        "action": action,
        "params": params,
        "product_id": product.product.id if product else None,
    }


def _sales_swing(db: Session, seller_id: uuid.UUID) -> list[dict]:
    yesterday = local_today() - timedelta(days=1)
    actual = period_metrics(db, seller_id, DateRange(yesterday, yesterday)).net_sales_cents
    same_weekdays = [yesterday - timedelta(days=7 * w) for w in range(1, 5)]
    usual = sum(period_metrics(db, seller_id, DateRange(d, d)).net_sales_cents for d in same_weekdays) / 4
    if usual < SALES_SWING_MIN_AVG_CENTS:
        return []
    pct = round((actual - usual) / usual * 100, 1)
    params = {"date": yesterday.isoformat(), "weekday": yesterday.weekday(), "actual_cents": actual,
              "usual_cents": round(usual), "pct": pct}
    if pct >= SALES_SWING_PCT:
        return [_insight("sales_spike", "low", "check_stock_for_demand", params)]
    if pct <= -SALES_SWING_PCT:
        return [_insight("sales_drop", "medium", "review_prices_and_stock", params)]
    return []


def _margin(db: Session, seller_id: uuid.UUID, products: list[ProductDemand]) -> list[dict]:
    insights = []
    m = period_metrics(db, seller_id, trailing_days(30))
    if (
        m.gross_margin_pct is not None
        and m.costed_net >= LOW_MARGIN_MIN_REVENUE_CENTS
        and m.gross_margin_pct < LOW_MARGIN_PCT
    ):
        insights.append(
            _insight("low_margin", "high", "review_prices", {"margin_pct": m.gross_margin_pct,
                                                             "threshold_pct": LOW_MARGIN_PCT})
        )
    for d in products:
        cost = d.product.cost_cents
        if cost is not None and d.product.price_cents <= cost:
            insights.append(
                _insight("below_cost", "high", "raise_price",
                         {"price_cents": d.product.price_cents, "cost_cents": cost}, d)
            )

    total30 = sum(d.revenue30_cents for d in products)
    if total30:
        for d in products:
            share = d.revenue30_cents / total30
            if d.product.cost_cents is None and share >= MISSING_COST_REVENUE_SHARE:
                insights.append(
                    _insight("missing_cost", "medium", "add_cost",
                             {"revenue_share_pct": round(share * 100, 1), "revenue_cents": d.revenue30_cents}, d)
                )
    return insights


def _stock(products: list[ProductDemand]) -> list[dict]:
    insights = []
    for d in products:
        if d.product.stock_pieces > 0 and d.days_remaining is not None and d.days_remaining <= STOCKOUT_DAYS:
            insights.append(
                _insight("stockout_risk", "high", "reorder",
                         {"days": round(d.days_remaining, 1), "reorder_pieces": d.suggested_reorder_pieces,
                          "unit_type": d.product.unit_type.value, "unit_label": d.product.unit_label}, d)
            )
        value = d.stock_value_cents
        if (
            d.days_remaining is not None
            and d.days_remaining > OVERSTOCK_DAYS
            and value is not None
            and value >= OVERSTOCK_MIN_VALUE_CENTS
        ):
            insights.append(
                _insight("overstock", "low", "promote_or_pause_restock",
                         {"days": round(d.days_remaining), "stock_value_cents": value}, d)
            )
    return insights


def _bestsellers(products: list[ProductDemand]) -> list[dict]:
    insights = []
    today = local_today()
    for d in products:
        recent = sum(d.series.get(today - timedelta(days=i), 0) for i in range(7)) / d.unit_divisor
        before = sum(d.series.get(today - timedelta(days=i), 0) for i in range(7, 28)) / d.unit_divisor / 3
        if recent >= BESTSELLER_MIN_UNITS and recent >= BESTSELLER_GROWTH * before:
            insights.append(
                _insight("emerging_bestseller", "low", "stock_up",
                         {"units_last_7_days": round(recent, 1), "weekly_avg_before": round(before, 1),
                          "growth": round(recent / before, 1) if before else None}, d)
            )
    return insights


def get_insights(db: Session, seller_id: uuid.UUID) -> list[dict]:
    products = load_demand(db, seller_id).products
    insights = [
        *_stock(products),
        *_margin(db, seller_id, products),
        *_sales_swing(db, seller_id),
        *_bestsellers(products),
    ]
    # Within a rule, surface the biggest cases first: soonest stockout, most money tied up, etc.
    insights.sort(key=lambda i: -(i["params"].get("stock_value_cents") or i["params"].get("revenue_cents") or 0))
    insights.sort(key=lambda i: i["params"]["days"] if i["code"] == "stockout_risk" else 0)

    kept, per_code = [], {}
    for insight in insights:
        per_code[insight["code"]] = per_code.get(insight["code"], 0) + 1
        if per_code[insight["code"]] <= MAX_PER_CODE:
            kept.append(insight)
    kept.sort(key=lambda i: SEVERITY_ORDER[i["severity"]])
    return kept[:MAX_INSIGHTS]
