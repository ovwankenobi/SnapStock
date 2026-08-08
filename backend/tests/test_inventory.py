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


def test_create_product_sets_initial_stock_movement(client):
    token = _register_seller(client)
    product = _create_bundle_product(client, token)

    assert product["stockPieces"] == 100
    assert product["piecesPerUnit"] == 10
    assert product["stockStatus"] == "in_stock"


def test_quick_sell_two_bundles_deducts_pieces_and_creates_walk_in_sale(client):
    token = _register_seller(client)
    product = _create_bundle_product(client, token)

    response = client.post(
        f"/api/v1/products/{product['id']}/quick-sell",
        json={"quantity": 2, "paymentMethod": "cash"},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["product"]["stockPieces"] == 80
    assert body["totalCents"] == 50000
    assert body["receiptCode"].startswith("WI-")


def test_quick_sell_more_than_available_stock_is_rejected_and_changes_nothing(client):
    token = _register_seller(client)
    product = _create_bundle_product(client, token, stockPieces=15)

    response = client.post(
        f"/api/v1/products/{product['id']}/quick-sell",
        json={"quantity": 2, "paymentMethod": "cash"},
        headers=_auth(token),
    )
    assert response.status_code == 400

    unchanged = client.get(f"/api/v1/products/{product['id']}", headers=_auth(token))
    assert unchanged.json()["stockPieces"] == 15


def test_low_stock_badge_appears_at_threshold(client):
    token = _register_seller(client)
    low = _create_bundle_product(
        client, token, name="Low Stock Item", stockPieces=20, lowStockThreshold=20
    )
    healthy = _create_bundle_product(
        client, token, name="Healthy Item", stockPieces=21, lowStockThreshold=20
    )

    low_stock = client.get("/api/v1/products/low-stock", headers=_auth(token)).json()
    ids = {item["id"] for item in low_stock}

    assert low["id"] in ids
    assert healthy["id"] not in ids


def test_restock_increases_stock(client):
    token = _register_seller(client)
    product = _create_bundle_product(client, token, stockPieces=10)

    response = client.post(
        f"/api/v1/products/{product['id']}/restock",
        json={"quantity": 50, "note": "weekly delivery"},
        headers=_auth(token),
    )
    assert response.status_code == 200
    assert response.json()["stockPieces"] == 60


def test_patch_does_not_change_stock(client):
    token = _register_seller(client)
    product = _create_bundle_product(client, token, stockPieces=10)

    response = client.patch(
        f"/api/v1/products/{product['id']}",
        json={"name": "Renamed", "priceCents": 30000},
        headers=_auth(token),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Renamed"
    assert body["priceCents"] == 30000
    assert body["stockPieces"] == 10


def test_soft_delete_hides_product_from_list(client):
    token = _register_seller(client)
    product = _create_bundle_product(client, token)

    delete_response = client.delete(f"/api/v1/products/{product['id']}", headers=_auth(token))
    assert delete_response.status_code == 204

    listing = client.get("/api/v1/products", headers=_auth(token)).json()
    ids = {item["id"] for item in listing["items"]}
    assert product["id"] not in ids


def test_seller_cannot_access_another_sellers_product(client):
    token_a = _register_seller(client)
    product = _create_bundle_product(client, token_a)

    token_b = _register_seller(
        client, email="other-seller@example.com", businessName="Other Store"
    )
    response = client.get(f"/api/v1/products/{product['id']}", headers=_auth(token_b))
    assert response.status_code == 404


def test_search_and_pagination(client):
    token = _register_seller(client)
    for i in range(3):
        _create_bundle_product(client, token, name=f"Rice Sack {i}", category="Rice")
    _create_bundle_product(client, token, name="Cooking Oil", category="Oil")

    search = client.get(
        "/api/v1/products", params={"search": "Rice"}, headers=_auth(token)
    ).json()
    assert search["total"] == 3

    page = client.get(
        "/api/v1/products", params={"page": 1, "page_size": 2}, headers=_auth(token)
    ).json()
    assert len(page["items"]) == 2
    assert page["total"] == 4
