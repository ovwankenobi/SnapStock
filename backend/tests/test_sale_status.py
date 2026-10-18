from app.database import SessionLocal
from app.models import ProductCostHistory, StockMovement
from test_analytics import _auth, _create_product, _register_seller


def _sell(client, token, items, **extra):
    response = client.post(
        "/api/v1/sales",
        json={"saleType": "walk_in", "paymentMethod": "cash", "items": items, **extra},
        headers=_auth(token),
    )
    return response


def _product(client, token, product_id):
    return client.get(f"/api/v1/products/{product_id}", headers=_auth(token)).json()


def test_edited_line_price_is_charged_without_changing_the_product(client):
    token = _register_seller(client)
    product = _create_product(client, token, priceCents=1000, stockPieces=10)

    response = _sell(
        client,
        token,
        [
            {"productId": product["id"], "quantity": 2, "unitPriceCents": 800},
            {"productId": product["id"], "quantity": 1},
        ],
    )
    assert response.status_code == 201, response.text
    sale = response.json()

    assert sale["subtotalCents"] == 2 * 800 + 1000
    assert sale["totalCents"] == sale["subtotalCents"]
    edited, default = sale["items"]
    assert edited["unitPriceCentsSnapshot"] == 800
    assert edited["listPriceCentsSnapshot"] == 1000
    assert edited["lineTotalCents"] == 1600
    assert default["unitPriceCentsSnapshot"] == 1000

    after = _product(client, token, product["id"])
    assert after["priceCents"] == 1000
    assert after["stockPieces"] == 7


def test_quick_sell_accepts_an_edited_price(client):
    token = _register_seller(client)
    product = _create_product(client, token, priceCents=500)

    response = client.post(
        f"/api/v1/products/{product['id']}/quick-sell",
        json={"quantity": 3, "paymentMethod": "cash", "unitPriceCents": 450},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["totalCents"] == 1350
    assert response.json()["product"]["priceCents"] == 500


def test_discount_is_taken_off_the_subtotal_and_cannot_exceed_it(client):
    token = _register_seller(client)
    product = _create_product(client, token, priceCents=1000)

    ok = _sell(client, token, [{"productId": product["id"], "quantity": 1}], discountCents=200)
    assert ok.status_code == 201, ok.text
    assert ok.json()["subtotalCents"] == 1000
    assert ok.json()["discountCents"] == 200
    assert ok.json()["totalCents"] == 800

    too_big = _sell(client, token, [{"productId": product["id"], "quantity": 1}], discountCents=1001)
    assert too_big.status_code == 400

    lump_sum = client.post(
        "/api/v1/sales",
        json={"saleType": "walk_in", "paymentMethod": "cash", "totalCents": 500, "discountCents": 50},
        headers=_auth(token),
    )
    assert lump_sum.status_code == 422


def test_void_returns_stock_once_and_drops_out_of_analytics(client):
    token = _register_seller(client)
    product = _create_product(client, token, priceCents=100, stockPieces=10)
    sale = _sell(client, token, [{"productId": product["id"], "quantity": 4}]).json()
    assert _product(client, token, product["id"])["stockPieces"] == 6

    voided = client.post(f"/api/v1/sales/{sale['id']}/void", json={"reason": "wrong item"}, headers=_auth(token))
    assert voided.status_code == 200, voided.text
    assert voided.json()["status"] == "voided"
    assert voided.json()["statusReason"] == "wrong item"
    assert _product(client, token, product["id"])["stockPieces"] == 10

    again = client.post(f"/api/v1/sales/{sale['id']}/void", json={}, headers=_auth(token))
    assert again.status_code == 409
    refund_after_void = client.post(f"/api/v1/sales/{sale['id']}/refund", json={}, headers=_auth(token))
    assert refund_after_void.status_code == 409
    assert _product(client, token, product["id"])["stockPieces"] == 10

    db = SessionLocal()
    try:
        reasons = [m.reason for m in db.query(StockMovement).filter(StockMovement.sale_id == sale["id"]).all()]
    finally:
        db.close()
    assert sorted(r.value for r in reasons) == ["sale", "void"]

    summary = client.get("/api/v1/analytics/summary", headers=_auth(token)).json()
    assert summary["todaySaleCount"] == 0
    assert summary["todayRevenueCents"] == 0

    receipt = client.get(f"/api/v1/sales/receipt/{sale['receiptCode']}").json()
    assert receipt["status"] == "voided"
    assert "wrong item" not in str(receipt)


def test_refund_returns_stock_and_is_reported_as_a_refund(client):
    token = _register_seller(client)
    product = _create_product(client, token, priceCents=100, stockPieces=10)
    sale = _sell(client, token, [{"productId": product["id"], "quantity": 3}]).json()

    refunded = client.post(f"/api/v1/sales/{sale['id']}/refund", json={}, headers=_auth(token))
    assert refunded.status_code == 200
    assert refunded.json()["status"] == "refunded"
    assert _product(client, token, product["id"])["stockPieces"] == 10

    overview = client.get("/api/v1/analytics/overview", params={"range": "today"}, headers=_auth(token)).json()
    assert overview["current"]["grossSalesCents"] == 300
    assert overview["current"]["refundsCents"] == 300
    assert overview["current"]["netSalesCents"] == 0
    assert overview["current"]["transactions"] == 0


def test_void_is_scoped_to_the_seller(client):
    token = _register_seller(client)
    other = _register_seller(client, email="other@example.com")
    product = _create_product(client, token)
    sale = _sell(client, token, [{"productId": product["id"], "quantity": 1}]).json()

    response = client.post(f"/api/v1/sales/{sale['id']}/void", json={}, headers=_auth(other))
    assert response.status_code == 404


def test_cost_is_snapshotted_so_later_cost_edits_keep_past_profit(client):
    token = _register_seller(client)
    product = _create_product(client, token, priceCents=1000, costCents=600)
    _sell(client, token, [{"productId": product["id"], "quantity": 2}])

    patched = client.patch(f"/api/v1/products/{product['id']}", json={"costCents": 900}, headers=_auth(token))
    assert patched.status_code == 200
    assert patched.json()["costCents"] == 900

    overview = client.get("/api/v1/analytics/overview", params={"range": "today"}, headers=_auth(token)).json()
    assert overview["current"]["cogsCents"] == 1200
    assert overview["current"]["grossProfitCents"] == 800
    assert overview["current"]["grossMarginPct"] == 40.0
    assert overview["current"]["costCoveragePct"] == 100.0


def test_restock_with_unit_cost_updates_cost_and_logs_history(client):
    token = _register_seller(client)
    product = _create_product(client, token, costCents=500)

    single = client.post(
        f"/api/v1/products/{product['id']}/restock", json={"quantity": 5, "unitCostCents": 550}, headers=_auth(token)
    )
    assert single.status_code == 200
    assert single.json()["costCents"] == 550

    bulk = client.post(
        "/api/v1/products/restock",
        json={"items": [{"productId": product["id"], "quantity": 5, "unitCostCents": 520}]},
        headers=_auth(token),
    )
    assert bulk.status_code == 200
    assert bulk.json()[0]["costCents"] == 520

    # Restocking without a cost keeps the current one.
    client.post(f"/api/v1/products/{product['id']}/restock", json={"quantity": 1}, headers=_auth(token))
    assert _product(client, token, product["id"])["costCents"] == 520

    db = SessionLocal()
    try:
        history = (
            db.query(ProductCostHistory)
            .filter(ProductCostHistory.product_id == product["id"])
            .order_by(ProductCostHistory.created_at)
            .all()
        )
    finally:
        db.close()
    assert [(h.cost_cents, h.source.value) for h in history] == [
        (500, "manual"),
        (550, "restock"),
        (520, "restock"),
    ]

