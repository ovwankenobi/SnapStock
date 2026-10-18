import uuid
from datetime import datetime, timedelta, timezone

from app.database import SessionLocal
from app.models import PaymentMethod, Sale, SaleItem, SaleStatus, SaleType, UnitType


def _register_seller(client, **overrides):
    payload = {
        "email": "seller@example.com",
        "password": "password123",
        "fullName": "Aling Nena",
        "role": "seller",
        "businessName": "Nena's Store",
        "businessType": "retail",
    }
    payload.update(overrides)
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["accessToken"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _create_product(client, token, **overrides):
    payload = {
        "name": "Kalamansi",
        "priceCents": 100,
        "unitType": "piece",
        "piecesPerUnit": 1,
        "stockPieces": 100,
        "lowStockThreshold": 10,
        "category": "Produce",
    }
    payload.update(overrides)
    response = client.post("/api/v1/products", json=payload, headers=_auth(token))
    assert response.status_code == 201, response.text
    return response.json()


def _insert_backdated_sale_item(
    seller_id,
    product_id,
    pieces,
    days_ago=0,
    price_cents=100,
    created_at=None,
    status=SaleStatus.COMPLETED,
    cost_cents=None,
    list_price_cents=None,
    discount_cents=0,
):
    db = SessionLocal()
    try:
        created_at = created_at or datetime.now(timezone.utc) - timedelta(days=days_ago)
        line_total = price_cents * pieces
        sale = Sale(
            seller_id=uuid.UUID(seller_id),
            buyer_id=None,
            sale_type=SaleType.WALK_IN,
            subtotal_cents=line_total,
            discount_cents=discount_cents,
            total_cents=line_total - discount_cents,
            status=status,
            payment_method=PaymentMethod.CASH,
            receipt_code=f"TST{uuid.uuid4().hex[:8].upper()}",
            created_at=created_at,
        )
        db.add(sale)
        db.flush()
        db.add(
            SaleItem(
                sale_id=sale.id,
                product_id=uuid.UUID(product_id),
                product_name_snapshot="Backdated Product",
                list_price_cents_snapshot=list_price_cents if list_price_cents is not None else price_cents,
                unit_price_cents_snapshot=price_cents,
                unit_cost_cents_snapshot=cost_cents,
                cost_total_cents=cost_cents * pieces if cost_cents is not None else None,
                quantity=pieces,
                unit_type_snapshot=UnitType.PIECE,
                pieces_deducted=pieces,
                line_total_cents=line_total,
            )
        )
        db.commit()
    finally:
        db.close()


def test_analytics_requires_seller_auth(client):
    assert client.get("/api/v1/analytics/summary").status_code == 401


def test_summary_counts_today_sales_and_low_stock(client):
    token = _register_seller(client)
    product = _create_product(client, token, stockPieces=5, lowStockThreshold=10)

    sell = client.post(
        f"/api/v1/products/{product['id']}/quick-sell",
        json={"quantity": 2, "paymentMethod": "cash"},
        headers=_auth(token),
    )
    assert sell.status_code == 200, sell.text

    summary = client.get("/api/v1/analytics/summary", headers=_auth(token)).json()
    assert summary["todaySaleCount"] == 1
    assert summary["todayRevenueCents"] == 200
    assert summary["lowStockCount"] == 1


def test_forecast_returns_null_for_brand_new_product(client):
    token = _register_seller(client)
    product = _create_product(client, token)

    forecast = client.get("/api/v1/analytics/forecast", headers=_auth(token)).json()
    entry = next(f for f in forecast["items"] if f["productId"] == product["id"])

    assert entry["avgDailyPiecesWeek"] is None
    assert entry["avgDailyPiecesMonth"] is None
    assert entry["daysOfStockRemaining"] is None
    assert entry["atRisk"] is False


def test_forecast_flags_at_risk_product_with_sufficient_history(client):
    token = _register_seller(client)
    me = client.get("/api/v1/auth/me", headers=_auth(token)).json()
    product = _create_product(client, token, stockPieces=20, lowStockThreshold=5)

    for days_ago in range(14):
        _insert_backdated_sale_item(me["id"], product["id"], pieces=5, days_ago=days_ago)

    forecast = client.get("/api/v1/analytics/forecast", headers=_auth(token)).json()
    entry = next(f for f in forecast["items"] if f["productId"] == product["id"])

    assert entry["avgDailyPiecesWeek"] == 5.0
    assert entry["daysOfStockRemaining"] == 4.0
    assert entry["atRisk"] is True


def test_forecast_ignores_history_older_than_thirty_days(client):
    token = _register_seller(client)
    me = client.get("/api/v1/auth/me", headers=_auth(token)).json()
    product = _create_product(client, token, stockPieces=50)

    for days_ago in range(10):
        _insert_backdated_sale_item(me["id"], product["id"], pieces=3, days_ago=days_ago + 40)

    forecast = client.get("/api/v1/analytics/forecast", headers=_auth(token)).json()
    entry = next(f for f in forecast["items"] if f["productId"] == product["id"])

    assert entry["avgDailyPiecesWeek"] is None


def test_sales_trend_fills_zero_days(client):
    token = _register_seller(client)
    product = _create_product(client, token)

    client.post(
        f"/api/v1/products/{product['id']}/quick-sell",
        json={"quantity": 1, "paymentMethod": "cash"},
        headers=_auth(token),
    )

    trend = client.get(
        "/api/v1/analytics/sales-trend", params={"range": "week"}, headers=_auth(token)
    ).json()

    assert len(trend) == 7
    assert trend[-1]["saleCount"] == 1
    assert trend[-1]["revenueCents"] == 100
    assert all(point["saleCount"] == 0 for point in trend[:-1])


def test_top_products_orders_by_revenue(client):
    token = _register_seller(client)
    product_a = _create_product(client, token, name="Cheap Item", priceCents=100)
    product_b = _create_product(client, token, name="Pricier Item", priceCents=1000)

    client.post(
        f"/api/v1/products/{product_a['id']}/quick-sell",
        json={"quantity": 5, "paymentMethod": "cash"},
        headers=_auth(token),
    )
    client.post(
        f"/api/v1/products/{product_b['id']}/quick-sell",
        json={"quantity": 1, "paymentMethod": "cash"},
        headers=_auth(token),
    )

    top = client.get(
        "/api/v1/analytics/top-products", params={"range": "week", "limit": 5}, headers=_auth(token)
    ).json()

    assert [item["productId"] for item in top] == [product_b["id"], product_a["id"]]
    assert top[0]["revenueCents"] == 1000
    assert top[1]["revenueCents"] == 500
