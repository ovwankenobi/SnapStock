from datetime import datetime, time, timedelta, timezone

from test_analytics import _auth, _create_product, _insert_backdated_sale_item, _register_seller

from app.core.business_time import BUSINESS_TZ, local_midnight_utc, local_today
from app.models import SaleStatus


def _me(client, token):
    return client.get("/api/v1/auth/me", headers=_auth(token)).json()


def test_business_day_starts_at_local_midnight_not_utc(client):
    token = _register_seller(client)
    me = _me(client, token)
    product = _create_product(client, token)
    midnight = local_midnight_utc(local_today())

    # One second either side of local midnight: yesterday vs today in Manila.
    _insert_backdated_sale_item(me["id"], product["id"], pieces=1, created_at=midnight - timedelta(seconds=1))
    _insert_backdated_sale_item(me["id"], product["id"], pieces=2, created_at=midnight + timedelta(seconds=1))

    summary = client.get("/api/v1/analytics/summary", headers=_auth(token)).json()
    assert summary["todaySaleCount"] == 1
    assert summary["todayRevenueCents"] == 200

    trend = client.get("/api/v1/analytics/sales-trend", params={"range": "week"}, headers=_auth(token)).json()
    assert trend[-1]["date"] == local_today().isoformat()
    assert trend[-1]["revenueCents"] == 200
    assert trend[-2]["revenueCents"] == 100

    sales = client.get("/api/v1/sales", params={"range": "today"}, headers=_auth(token)).json()
    assert sales["total"] == 1


def test_overview_reconciles_gross_to_net_and_excludes_voids(client):
    token = _register_seller(client)
    me = _me(client, token)
    product = _create_product(client, token)

    # Listed at 120, sold 2 at 100 (cost 60), 20 off the sale: total 180.
    _insert_backdated_sale_item(
        me["id"], product["id"], pieces=2, price_cents=100, list_price_cents=120, cost_cents=60, discount_cents=20
    )
    _insert_backdated_sale_item(me["id"], product["id"], pieces=3, status=SaleStatus.REFUNDED)
    _insert_backdated_sale_item(me["id"], product["id"], pieces=5, status=SaleStatus.VOIDED)

    overview = client.get("/api/v1/analytics/overview", params={"range": "today"}, headers=_auth(token)).json()
    current = overview["current"]
    assert current["grossSalesCents"] == 240 + 300
    assert current["priceAdjustmentsCents"] == 40
    assert current["discountsCents"] == 20
    assert current["refundsCents"] == 300
    assert current["netSalesCents"] == 180
    assert (
        current["grossSalesCents"]
        - current["priceAdjustmentsCents"]
        - current["discountsCents"]
        - current["refundsCents"]
        == current["netSalesCents"]
    )
    assert current["transactions"] == 1
    assert current["unitsSold"] == 2
    assert current["avgTransactionCents"] == 180
    assert current["cogsCents"] == 120
    # Revenue after the discount (180) minus cost (120).
    assert current["grossProfitCents"] == 60
    assert current["grossMarginPct"] == 33.3
    assert current["costCoveragePct"] == 100.0


def test_a_markup_counts_as_a_negative_price_adjustment(client):
    token = _register_seller(client)
    me = _me(client, token)
    product = _create_product(client, token)
    _insert_backdated_sale_item(me["id"], product["id"], pieces=2, price_cents=150, list_price_cents=100)

    current = client.get("/api/v1/analytics/overview", params={"range": "today"}, headers=_auth(token)).json()[
        "current"
    ]
    assert current["grossSalesCents"] == 200
    assert current["priceAdjustmentsCents"] == -100
    assert current["netSalesCents"] == 300


def test_overview_compares_with_the_previous_equal_period(client):
    token = _register_seller(client)
    me = _me(client, token)
    product = _create_product(client, token)
    _insert_backdated_sale_item(me["id"], product["id"], pieces=3, days_ago=1)
    _insert_backdated_sale_item(me["id"], product["id"], pieces=2, days_ago=8)

    overview = client.get("/api/v1/analytics/overview", params={"range": "week"}, headers=_auth(token)).json()
    assert overview["current"]["netSalesCents"] == 300
    assert overview["previous"]["netSalesCents"] == 200
    assert overview["changePct"]["netSalesCents"] == 50.0
    assert overview["previousEnd"] == (local_today() - timedelta(days=7)).isoformat()


def test_custom_range_needs_valid_dates(client):
    token = _register_seller(client)
    url = "/api/v1/analytics/overview"
    assert client.get(url, params={"range": "custom"}, headers=_auth(token)).status_code == 400
    backwards = {"range": "custom", "start": "2026-10-10", "end": "2026-10-01"}
    assert client.get(url, params=backwards, headers=_auth(token)).status_code == 400

    ok = {"range": "custom", "start": "2026-10-01", "end": "2026-10-10"}
    trend = client.get("/api/v1/analytics/sales-trend", params=ok, headers=_auth(token)).json()
    assert len(trend) == 10


def test_sales_trend_buckets_by_month(client):
    token = _register_seller(client)
    params = {"range": "custom", "start": "2026-08-15", "end": "2026-10-05", "granularity": "month"}
    trend = client.get("/api/v1/analytics/sales-trend", params=params, headers=_auth(token)).json()
    assert [p["date"] for p in trend] == ["2026-08-01", "2026-09-01", "2026-10-01"]


def test_top_products_can_sort_by_quantity_and_profit(client):
    token = _register_seller(client)
    me = _me(client, token)
    volume = _create_product(client, token, name="Volume")
    margin = _create_product(client, token, name="Margin")
    _insert_backdated_sale_item(me["id"], volume["id"], pieces=10, price_cents=100, cost_cents=95)
    _insert_backdated_sale_item(me["id"], margin["id"], pieces=2, price_cents=400, cost_cents=100)

    def top(sort):
        params = {"range": "today", "sort": sort}
        return client.get("/api/v1/analytics/top-products", params=params, headers=_auth(token)).json()

    assert [p["productId"] for p in top("quantity")] == [volume["id"], margin["id"]]
    by_profit = top("profit")
    assert [p["productId"] for p in by_profit] == [margin["id"], volume["id"]]
    assert by_profit[0]["grossProfitCents"] == 600
    assert by_profit[0]["marginPct"] == 75.0


def test_patterns_bucket_by_local_weekday_and_hour(client):
    token = _register_seller(client)
    me = _me(client, token)
    product = _create_product(client, token)
    yesterday = local_today() - timedelta(days=1)
    at = datetime.combine(yesterday, time(10, 30), tzinfo=BUSINESS_TZ)
    _insert_backdated_sale_item(me["id"], product["id"], pieces=8, created_at=at.astimezone(timezone.utc))

    patterns = client.get("/api/v1/analytics/patterns", params={"weeks": 4}, headers=_auth(token)).json()
    assert patterns["weekdays"][yesterday.weekday()]["avgRevenueCents"] == 200  # 800 over 4 such days
    assert patterns["hours"][10]["avgTransactions"] == round(1 / 28, 2)
    assert sum(h["avgRevenueCents"] for h in patterns["hours"] if h["hour"] != 10) == 0


def test_inventory_health_classifies_products_and_suggests_reorders(client):
    token = _register_seller(client)
    me = _me(client, token)
    out = _create_product(client, token, name="Out", stockPieces=0)
    risky = _create_product(client, token, name="Risky", stockPieces=20, lowStockThreshold=0, costCents=50)
    slow = _create_product(client, token, name="Slow", stockPieces=50, lowStockThreshold=0)
    fresh = _create_product(client, token, name="Fresh", stockPieces=50, lowStockThreshold=0)
    for days_ago in range(14):
        _insert_backdated_sale_item(me["id"], risky["id"], pieces=5, days_ago=days_ago)
    _insert_backdated_sale_item(me["id"], slow["id"], pieces=1, days_ago=20)

    rows = {r["productId"]: r for r in client.get("/api/v1/analytics/inventory", headers=_auth(token)).json()}
    assert rows[out["id"]]["status"] == "out_of_stock"
    assert rows[risky["id"]]["status"] == "stockout_risk"
    assert rows[risky["id"]]["daysRemaining"] == 4.0
    # 14 days at 5/day + 3 days of safety stock - 20 on hand.
    assert rows[risky["id"]]["suggestedReorderPieces"] == 70 + 15 - 20
    assert rows[risky["id"]]["stockValueCents"] == 1000
    assert rows[risky["id"]]["turnover30"] == 3.5
    assert rows[slow["id"]]["status"] == "slow_moving"
    assert rows[fresh["id"]]["status"] == "healthy"


def test_forecast_uses_a_fallback_for_new_products(client):
    token = _register_seller(client)
    me = _me(client, token)
    product = _create_product(client, token, stockPieces=100)
    for days_ago in range(3):
        _insert_backdated_sale_item(me["id"], product["id"], pieces=7, days_ago=days_ago)

    forecast = client.get("/api/v1/analytics/forecast", headers=_auth(token)).json()
    entry = next(f for f in forecast["items"] if f["productId"] == product["id"])
    assert entry["method"] == "fallback"
    assert entry["confidence"] == "low"
    assert entry["dailyRate"] == 3.0  # 21 pieces over the 7-day minimum
    assert entry["forecast7"] == 21.0
    assert entry["forecast14"] == 42.0
    assert forecast["weekdayAdjusted"] is False


def _insights(client, token):
    return client.get("/api/v1/analytics/insights", headers=_auth(token)).json()


def test_insights_are_quiet_for_a_new_shop(client):
    token = _register_seller(client)
    _create_product(client, token)
    assert _insights(client, token) == []


def test_insights_flag_stock_cost_and_margin_risks(client):
    token = _register_seller(client)
    me = _me(client, token)
    risky = _create_product(client, token, name="Risky", priceCents=1000, stockPieces=10, costCents=950)
    _create_product(client, token, name="Loss Leader", priceCents=100, costCents=120)
    uncosted = _create_product(client, token, name="Uncosted", stockPieces=1000)
    for days_ago in range(14):
        # 95% cost on a busy line drags the shop's margin under 10%.
        _insert_backdated_sale_item(
            me["id"], risky["id"], pieces=10, days_ago=days_ago, price_cents=1000, cost_cents=950
        )
        _insert_backdated_sale_item(me["id"], uncosted["id"], pieces=10, days_ago=days_ago, price_cents=1000)

    insights = _insights(client, token)
    by_code = {i["code"]: i for i in insights}
    assert by_code["stockout_risk"]["productId"] == risky["id"]
    assert by_code["stockout_risk"]["params"]["days"] == 1.0
    assert by_code["below_cost"]["params"]["product"] == "Loss Leader"
    assert by_code["missing_cost"]["productId"] == uncosted["id"]
    assert by_code["low_margin"]["params"]["marginPct"] == 5.0
    severities = [i["severity"] for i in insights]
    assert severities == sorted(severities, key=["high", "medium", "low"].index)


def test_insights_spot_emerging_bestsellers_and_sales_drops(client):
    token = _register_seller(client)
    me = _me(client, token)
    steady = _create_product(client, token, name="Steady", stockPieces=10_000)
    # 1,000 pesos on each of the previous four same-weekdays, nothing yesterday.
    for weeks in range(1, 5):
        _insert_backdated_sale_item(me["id"], steady["id"], pieces=1000, days_ago=1 + 7 * weeks)
    rising = _create_product(client, token, name="Rising", stockPieces=10_000)
    for days_ago in range(3):
        _insert_backdated_sale_item(me["id"], rising["id"], pieces=10, days_ago=days_ago)

    by_code = {i["code"]: i for i in _insights(client, token)}
    # Yesterday only had Rising's 10 pesos against a usual 1,000.
    assert by_code["sales_drop"]["params"]["pct"] == -99.0
    assert by_code["emerging_bestseller"]["productId"] == rising["id"]
    assert by_code["emerging_bestseller"]["params"]["unitsLast7Days"] == 30


def test_insights_cap_each_rule_and_keep_the_biggest_cases(client):
    token = _register_seller(client)
    me = _me(client, token)
    for i in range(5):
        # Lots of costly stock, a trickle of sales: overstocked, worth more as i grows.
        product = _create_product(
            client, token, name=f"Slow {i}", stockPieces=1000 * (i + 1), lowStockThreshold=0, costCents=100
        )
        for days_ago in range(14):
            _insert_backdated_sale_item(me["id"], product["id"], pieces=1, days_ago=days_ago)

    overstock = [i for i in _insights(client, token) if i["code"] == "overstock"]
    assert [i["params"]["product"] for i in overstock] == ["Slow 4", "Slow 3", "Slow 2"]
