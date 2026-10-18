from datetime import date, timedelta

import pytest

from app.services.analytics import forecast as fc

TODAY = date(2026, 10, 18)  # a Sunday


def _series(days: int, per_day: float, end: date = TODAY) -> dict[date, float]:
    return {end - timedelta(days=i): per_day for i in range(days)}


def test_no_sales_means_no_estimate():
    estimate = fc.estimate_demand({}, TODAY, None)
    assert estimate.method == "none"
    assert estimate.daily_rate is None


def test_low_history_uses_fallback_over_days_since_first_sale():
    # Sold 6 a day for the last 5 days: fallback divides by at least 7 days.
    series = _series(5, 6)
    estimate = fc.estimate_demand(series, TODAY, TODAY - timedelta(days=4))
    assert estimate.method == "fallback"
    assert estimate.confidence == "low"
    assert estimate.daily_rate == pytest.approx(30 / 7)
    assert estimate.avg_daily_week is None


def test_fallback_for_a_product_that_stopped_selling_is_zero():
    series = {TODAY - timedelta(days=45): 10}
    estimate = fc.estimate_demand(series, TODAY, TODAY - timedelta(days=45))
    assert estimate.method == "fallback"
    assert estimate.daily_rate == 0
    assert fc.days_of_stock(50, estimate.daily_rate) is None


def test_history_blends_week_and_month_averages():
    # 2/day for 30 days, then the last 7 days at 10/day.
    series = _series(30, 2)
    series.update(_series(7, 10))
    estimate = fc.estimate_demand(series, TODAY, TODAY - timedelta(days=40))
    assert estimate.method == "history"
    avg_month = (23 * 2 + 7 * 10) / 30
    assert estimate.avg_daily_week == 10
    assert estimate.avg_daily_month == pytest.approx(avg_month)
    assert estimate.daily_rate == pytest.approx(0.6 * 10 + 0.4 * avg_month)


def test_steady_long_history_is_high_confidence_and_spiky_is_medium():
    steady = fc.estimate_demand(_series(30, 5), TODAY, TODAY - timedelta(days=60))
    assert steady.confidence == "high"

    spiky = {TODAY - timedelta(days=i): (40 if i % 2 else 1) for i in range(30)}
    assert fc.estimate_demand(spiky, TODAY, TODAY - timedelta(days=60)).confidence == "medium"


def test_weekday_factors_need_four_weeks_and_are_clamped():
    assert fc.weekday_factors(_series(20, 100), TODAY, TODAY - timedelta(days=19)) is None

    # Saturdays sell 10x every other day: the raw factor (~4.4) is clamped to 2.0.
    shop = {}
    for i in range(56):
        day = TODAY - timedelta(days=i)
        shop[day] = 1000 if day.weekday() == 5 else 100
    factors = fc.weekday_factors(shop, TODAY, TODAY - timedelta(days=55))
    assert factors[5] == fc.WEEKDAY_FACTOR_MAX
    assert factors[0] == fc.WEEKDAY_FACTOR_MIN

    # Saturdays at 2x: within the clamp, so factors are the plain ratio to the overall mean.
    for day in shop:
        shop[day] = 200 if day.weekday() == 5 else 100
    factors = fc.weekday_factors(shop, TODAY, TODAY - timedelta(days=55))
    assert factors[5] == pytest.approx(200 / (800 / 7))
    assert factors[0] == pytest.approx(100 / (800 / 7))


def test_forecast_total_applies_weekday_factors():
    factors = [1.0] * 7
    factors[TODAY.weekday()] = 2.0
    assert fc.forecast_total(3, TODAY, 7, None) == 21
    assert fc.forecast_total(3, TODAY, 7, factors) == 24
    assert fc.forecast_total(None, TODAY, 7, factors) is None


def test_backtest_scores_a_perfectly_steady_product_at_100():
    series = _series(60, 4)
    accuracy = fc.backtest_accuracy({"p": series}, {"p": TODAY - timedelta(days=59)}, series, TODAY - timedelta(days=59), TODAY)
    assert accuracy == 100.0


def test_backtest_penalises_a_missed_spike_and_is_none_without_sales():
    series = _series(60, 4)
    series.update({TODAY - timedelta(days=i): 12 for i in range(1, 8)})
    accuracy = fc.backtest_accuracy({"p": series}, {"p": TODAY - timedelta(days=59)}, {}, None, TODAY)
    # Predicted 28 vs actual 84 over the week -> WAPE 66.7%.
    assert accuracy == pytest.approx(33.3, abs=0.1)

    assert fc.backtest_accuracy({"p": {}}, {}, {}, None, TODAY) is None
