"""Demand forecasting math (P4).

Pure functions over per-day sales series keyed by local date, so the method
can be unit-tested without a database. Quantities are stock pieces (or
thousandths for measure products) — whatever unit the series is in comes out.
"""

import math
from dataclasses import dataclass
from datetime import date, timedelta

# A product needs this many distinct selling days in the last 30 to use its own history.
MIN_HISTORY_DAYS = 14
HIGH_CONFIDENCE_DAYS = 21
HIGH_CONFIDENCE_MAX_CV = 0.6
WEEK_WEIGHT = 0.6
MONTH_WEIGHT = 0.4
# Weekday factors need four weeks of shop history and are clamped so one odd day can't dominate.
WEEKDAY_MIN_HISTORY_DAYS = 28
WEEKDAY_FACTOR_WEEKS = 8
WEEKDAY_FACTOR_MIN = 0.5
WEEKDAY_FACTOR_MAX = 2.0
FALLBACK_MIN_DIVISOR_DAYS = 7
BACKTEST_DAYS = 7


@dataclass(frozen=True)
class DemandEstimate:
    method: str  # "history" | "fallback" | "none"
    confidence: str  # "high" | "medium" | "low"
    daily_rate: float | None
    avg_daily_week: float | None
    avg_daily_month: float | None
    history_days: int


def window_sum(series: dict[date, float], end: date, days: int) -> float:
    """Total over the `days` local days ending on `end` (inclusive)."""
    return sum(series.get(end - timedelta(days=i), 0) for i in range(days))


def selling_days(series: dict[date, float], end: date, days: int) -> int:
    return sum(1 for i in range(days) if series.get(end - timedelta(days=i), 0) > 0)


def coefficient_of_variation(values: list[float]) -> float | None:
    if not values:
        return None
    mean = sum(values) / len(values)
    if mean == 0:
        return None
    variance = sum((v - mean) ** 2 for v in values) / len(values)
    return math.sqrt(variance) / mean


def estimate_demand(series: dict[date, float], as_of: date, first_sale: date | None) -> DemandEstimate:
    """Daily demand rate as of the end of local day `as_of`, using only data up to that day."""
    if first_sale is None or first_sale > as_of:
        return DemandEstimate("none", "low", None, None, None, 0)

    history_days = selling_days(series, as_of, 30)
    # Don't spread a product's sales over days before it was ever sold.
    days_known = (as_of - first_sale).days + 1

    if history_days >= MIN_HISTORY_DAYS:
        avg_week = window_sum(series, as_of, 7) / min(7, days_known)
        avg_month = window_sum(series, as_of, 30) / min(30, days_known)
        rate = WEEK_WEIGHT * avg_week + MONTH_WEIGHT * avg_month
        cv = coefficient_of_variation([series.get(as_of - timedelta(days=i), 0) for i in range(28)])
        if history_days >= HIGH_CONFIDENCE_DAYS and cv is not None and cv <= HIGH_CONFIDENCE_MAX_CV:
            confidence = "high"
        else:
            confidence = "medium"
        return DemandEstimate("history", confidence, rate, avg_week, avg_month, history_days)

    # Too little history for its own pattern: average what it sold recently over the time it's been selling.
    divisor = max(FALLBACK_MIN_DIVISOR_DAYS, min(30, days_known))
    rate = window_sum(series, as_of, 30) / divisor
    return DemandEstimate("fallback", "low", rate, None, None, history_days)


def weekday_factors(shop_daily: dict[date, float], as_of: date, first_sale: date | None) -> list[float] | None:
    """Monday..Sunday multipliers from the shop's last 8 weeks, or None if there isn't enough history."""
    if first_sale is None or (as_of - first_sale).days + 1 < WEEKDAY_MIN_HISTORY_DAYS:
        return None
    days = min(WEEKDAY_FACTOR_WEEKS * 7, (as_of - first_sale).days + 1)
    totals = [0.0] * 7
    counts = [0] * 7
    for i in range(days):
        day = as_of - timedelta(days=i)
        totals[day.weekday()] += shop_daily.get(day, 0)
        counts[day.weekday()] += 1
    overall = sum(totals) / sum(counts)
    if overall == 0:
        return None
    return [
        min(WEEKDAY_FACTOR_MAX, max(WEEKDAY_FACTOR_MIN, (totals[w] / counts[w]) / overall)) if counts[w] else 1.0
        for w in range(7)
    ]


def forecast_total(rate: float | None, start: date, days: int, factors: list[float] | None) -> float | None:
    """Expected demand over the `days` local days beginning on `start`."""
    if rate is None:
        return None
    return sum(rate * (factors[(start + timedelta(days=i)).weekday()] if factors else 1.0) for i in range(days))


def days_of_stock(stock: int, rate: float | None) -> float | None:
    if rate is None or rate <= 0:
        return None
    return stock / rate


def backtest_accuracy(
    series_by_product: dict[object, dict[date, float]],
    first_sale_by_product: dict[object, date],
    shop_daily: dict[date, float],
    shop_first_sale: date | None,
    today: date,
) -> float | None:
    """Forecast the last 7 complete days from data before them and score it as 100 - WAPE%.

    Returns None when nothing sold in the test window (accuracy is undefined).
    """
    test_start = today - timedelta(days=BACKTEST_DAYS)
    as_of = test_start - timedelta(days=1)
    factors = weekday_factors(shop_daily, as_of, shop_first_sale)

    abs_error = 0.0
    actual_total = 0.0
    for product_id, series in series_by_product.items():
        estimate = estimate_demand(series, as_of, first_sale_by_product.get(product_id))
        predicted = forecast_total(estimate.daily_rate, test_start, BACKTEST_DAYS, factors) or 0.0
        actual = window_sum(series, today - timedelta(days=1), BACKTEST_DAYS)
        abs_error += abs(predicted - actual)
        actual_total += actual
    if actual_total == 0:
        return None
    return round(max(0.0, 100 - abs_error / actual_total * 100), 1)
