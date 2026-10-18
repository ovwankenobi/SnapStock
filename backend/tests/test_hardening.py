import pytest
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.product import Product, UnitType
from app.models.stock_movement import StockMovementReason
from app.services.inventory import InsufficientStockError, apply_stock_change


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


def _register_buyer(client, **overrides):
    payload = {
        "email": "buyer@example.com",
        "password": "password123",
        "fullName": "Mang Jun",
        "role": "buyer",
    }
    payload.update(overrides)
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["accessToken"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _create_bundle_product(client, token, **overrides):
    payload = {
        "name": "Eggs (Tray)",
        "priceCents": 25000,
        "unitType": "bundle",
        "piecesPerUnit": 10,
        "stockPieces": 100,
        "lowStockThreshold": 20,
        "category": "Eggs",
    }
    payload.update(overrides)
    response = client.post("/api/v1/products", json=payload, headers=_auth(token))
    assert response.status_code == 201, response.text
    return response.json()


# --- Stock can never go negative -------------------------------------------------


def test_apply_stock_change_rejects_change_that_would_go_negative(client):
    token = _register_seller(client)
    product = _create_bundle_product(client, token, stockPieces=5)

    db: Session = SessionLocal()
    try:
        db_product = db.get(Product, product["id"])
        with pytest.raises(InsufficientStockError):
            apply_stock_change(
                db, db_product, change_pieces=-6, reason=StockMovementReason.CORRECTION
            )
        db.rollback()
    finally:
        db.close()

    unchanged = client.get(f"/api/v1/products/{product['id']}", headers=_auth(token))
    assert unchanged.json()["stockPieces"] == 5


def test_quick_sell_cannot_push_stock_below_zero_via_the_api(client):
    token = _register_seller(client)
    product = _create_bundle_product(client, token, stockPieces=9)  # < 1 bundle (10 pieces)

    response = client.post(
        f"/api/v1/products/{product['id']}/quick-sell",
        json={"quantity": 1, "paymentMethod": "cash"},
        headers=_auth(token),
    )
    assert response.status_code == 400

    unchanged = client.get(f"/api/v1/products/{product['id']}", headers=_auth(token))
    assert unchanged.json()["stockPieces"] == 9


# --- Bundle math ------------------------------------------------------------------


def test_itemized_sale_of_a_bundle_product_deducts_pieces_per_unit(client):
    seller_token = _register_seller(client)
    product = _create_bundle_product(client, seller_token, piecesPerUnit=12, stockPieces=120)
    buyer_token = _register_buyer(client)

    response = client.post(
        f"/api/v1/catalog/products/{product['id']}/order",
        json={"quantity": 3, "paymentMethod": "gcash"},
        headers=_auth(buyer_token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["items"][0]["piecesDeducted"] == 36  # 3 bundles * 12 pieces
    assert body["totalCents"] == 3 * product["priceCents"]

    remaining = client.get(f"/api/v1/products/{product['id']}", headers=_auth(seller_token))
    assert remaining.json()["stockPieces"] == 120 - 36


# --- Walk-in sales never reference a buyer -----------------------------------------


def test_quick_sell_walk_in_sale_has_no_buyer_reference(client):
    token = _register_seller(client)
    product = _create_bundle_product(client, token)

    quick_sell = client.post(
        f"/api/v1/products/{product['id']}/quick-sell",
        json={"quantity": 1, "paymentMethod": "cash"},
        headers=_auth(token),
    ).json()

    sale = client.get(f"/api/v1/sales/{quick_sell['saleId']}", headers=_auth(token)).json()
    assert sale["saleType"] == "walk_in"
    assert sale["buyerId"] is None
    assert sale["buyerName"] is None


def test_manual_walk_in_sale_via_checkout_has_no_buyer_reference(client):
    token = _register_seller(client)

    response = client.post(
        "/api/v1/sales",
        json={"saleType": "walk_in", "paymentMethod": "cash", "totalCents": 15000},
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["buyerId"] is None
    assert body["items"] == []


def test_walk_in_sale_cannot_be_given_a_buyer_id(client):
    token = _register_seller(client)
    buyer_token = _register_buyer(client)
    buyer_id = client.get("/api/v1/auth/me", headers=_auth(buyer_token)).json()["id"]

    response = client.post(
        "/api/v1/sales",
        json={
            "saleType": "walk_in",
            "buyerId": buyer_id,
            "paymentMethod": "cash",
            "totalCents": 15000,
        },
        headers=_auth(token),
    )
    assert response.status_code == 422


# --- Public receipt leaks no private fields -----------------------------------------


def test_public_receipt_endpoint_leaks_no_private_fields(client):
    seller_token = _register_seller(client)
    product = _create_bundle_product(client, seller_token, priceCents=5000, piecesPerUnit=1, stockPieces=50)
    buyer_token = _register_buyer(client)
    buyer = client.get("/api/v1/auth/me", headers=_auth(buyer_token)).json()

    order = client.post(
        f"/api/v1/catalog/products/{product['id']}/order",
        json={"quantity": 2, "paymentMethod": "gcash"},
        headers=_auth(buyer_token),
    ).json()

    response = client.get(f"/api/v1/sales/receipt/{order['receiptCode']}")
    assert response.status_code == 200
    body = response.json()

    assert set(body.keys()) == {
        "businessName",
        "receiptCode",
        "saleType",
        "items",
        "subtotalCents",
        "discountCents",
        "totalCents",
        "status",
        "paymentMethod",
        "createdAt",
    }
    # No seller/buyer identity, email, phone, or internal ids should ever appear.
    serialized = str(body)
    assert seller_token not in serialized
    assert buyer["email"] not in serialized
    assert buyer["fullName"] not in serialized
    assert order["id"] not in serialized
    assert order["sellerId"] not in serialized
    assert order["buyerId"] not in serialized


def test_public_receipt_unknown_code_is_404(client):
    response = client.get("/api/v1/sales/receipt/DOESNOTEXIST")
    assert response.status_code == 404


# --- Role guards reject the wrong role ----------------------------------------------


def test_buyer_cannot_create_or_quick_sell_products(client):
    seller_token = _register_seller(client)
    product = _create_bundle_product(client, seller_token)
    buyer_token = _register_buyer(client)

    create = client.post(
        "/api/v1/products",
        json={"name": "Rice", "priceCents": 100, "unitType": "piece"},
        headers=_auth(buyer_token),
    )
    assert create.status_code == 403

    quick_sell = client.post(
        f"/api/v1/products/{product['id']}/quick-sell",
        json={"quantity": 1, "paymentMethod": "cash"},
        headers=_auth(buyer_token),
    )
    assert quick_sell.status_code == 403


def test_buyer_cannot_record_a_seller_sale(client):
    _register_seller(client)
    buyer_token = _register_buyer(client)

    response = client.post(
        "/api/v1/sales",
        json={"saleType": "walk_in", "paymentMethod": "cash", "totalCents": 10000},
        headers=_auth(buyer_token),
    )
    assert response.status_code == 403


def test_seller_cannot_place_a_catalog_order(client):
    seller_token = _register_seller(client)
    product = _create_bundle_product(client, seller_token)

    response = client.post(
        f"/api/v1/catalog/products/{product['id']}/order",
        json={"quantity": 1, "paymentMethod": "cash"},
        headers=_auth(seller_token),
    )
    assert response.status_code == 403


def test_unauthenticated_requests_are_rejected_not_leaked(client):
    assert client.get("/api/v1/products").status_code == 401
    assert client.post("/api/v1/sales", json={}).status_code == 401


# --- Auth rate limiting -------------------------------------------------------------


def test_register_endpoint_is_rate_limited(client):
    for i in range(5):
        client.post(
            "/api/v1/auth/register",
            json={
                "email": f"burst{i}@example.com",
                "password": "password123",
                "fullName": "Burst Tester",
                "role": "buyer",
            },
        )

    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "burst-overflow@example.com",
            "password": "password123",
            "fullName": "Burst Tester",
            "role": "buyer",
        },
    )
    assert response.status_code == 429
    assert response.json()["detail"]


def test_login_endpoint_is_rate_limited(client):
    _register_seller(client)

    for _ in range(10):
        client.post(
            "/api/v1/auth/login",
            data={"username": "seller@example.com", "password": "wrong"},
        )

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "seller@example.com", "password": "wrong"},
    )
    assert response.status_code == 429
