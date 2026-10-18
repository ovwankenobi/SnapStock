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


def test_bulk_restock_increases_stock_on_every_product(client):
    token = _register_seller(client)
    eggs = _create_bundle_product(client, token, stockPieces=10)
    rice = _create_bundle_product(client, token, name="Rice", stockPieces=5)

    response = client.post(
        "/api/v1/products/restock",
        json={
            "items": [
                {"productId": eggs["id"], "quantity": 30},
                {"productId": rice["id"], "quantity": 20},
                {"productId": eggs["id"], "quantity": 10},
            ],
            "note": "weekly delivery",
        },
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    stock = {item["id"]: item["stockPieces"] for item in response.json()}
    assert stock == {eggs["id"]: 50, rice["id"]: 25}


def test_bulk_restock_with_another_sellers_product_changes_nothing(client):
    token_a = _register_seller(client)
    own = _create_bundle_product(client, token_a, stockPieces=10)

    token_b = _register_seller(
        client, email="other-seller@example.com", businessName="Other Store"
    )
    foreign = _create_bundle_product(client, token_b, stockPieces=10)

    response = client.post(
        "/api/v1/products/restock",
        json={
            "items": [
                {"productId": own["id"], "quantity": 5},
                {"productId": foreign["id"], "quantity": 5},
            ]
        },
        headers=_auth(token_a),
    )
    assert response.status_code == 404

    unchanged = client.get(f"/api/v1/products/{own['id']}", headers=_auth(token_a))
    assert unchanged.json()["stockPieces"] == 10


def test_bulk_restock_rejects_empty_items(client):
    token = _register_seller(client)
    response = client.post("/api/v1/products/restock", json={"items": []}, headers=_auth(token))
    assert response.status_code == 422


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


def test_categories_lists_distinct_active_categories_for_seller_only(client):
    token = _register_seller(client)
    _create_bundle_product(client, token, name="Eggs A", category="Eggs")
    _create_bundle_product(client, token, name="Eggs B", category="Eggs")
    _create_bundle_product(client, token, name="Rice", category="rice")
    _create_bundle_product(client, token, name="No Category", category=None)
    deleted = _create_bundle_product(client, token, name="Old", category="Discontinued")
    client.delete(f"/api/v1/products/{deleted['id']}", headers=_auth(token))

    other_token = _register_seller(client, email="other@example.com")
    _create_bundle_product(client, other_token, category="Secret")

    response = client.get("/api/v1/products/categories", headers=_auth(token))
    assert response.status_code == 200
    assert response.json() == ["Eggs", "rice"]


def test_delete_category_clears_it_from_own_products_only(client):
    token = _register_seller(client)
    eggs = _create_bundle_product(client, token, name="Eggs A", category="Eggs")
    rice = _create_bundle_product(client, token, name="Rice", category="Rice")

    other_token = _register_seller(client, email="other@example.com")
    other_eggs = _create_bundle_product(client, other_token, category="Eggs")

    response = client.delete("/api/v1/products/categories", params={"name": "Eggs"}, headers=_auth(token))
    assert response.status_code == 204

    assert client.get(f"/api/v1/products/{eggs['id']}", headers=_auth(token)).json()["category"] is None
    assert client.get(f"/api/v1/products/{rice['id']}", headers=_auth(token)).json()["category"] == "Rice"
    assert client.get("/api/v1/products/categories", headers=_auth(token)).json() == ["Rice"]
    other = client.get(f"/api/v1/products/{other_eggs['id']}", headers=_auth(other_token)).json()
    assert other["category"] == "Eggs"


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


def test_search_by_image_matches_only_own_products(client):
    token_a = _register_seller(client)
    own = _create_bundle_product(client, token_a, name="Rice Sack")
    token_b = _register_seller(
        client, email="other-seller@example.com", businessName="Other Store"
    )
    _create_bundle_product(client, token_b, name="Rice Sack")

    response = client.post(
        "/api/v1/products/search-by-image",
        data={"query": "rice"},
        files={"file": ("photo.jpg", b"fake-bytes", "image/jpeg")},
        headers=_auth(token_a),
    )
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "rice"
    assert [r["product"]["id"] for r in body["results"]] == [own["id"]]
    assert body["results"][0]["confidence"] is None

    empty = client.post(
        "/api/v1/products/search-by-image",
        data={"query": "durian"},
        files={"file": ("photo.jpg", b"fake-bytes", "image/jpeg")},
        headers=_auth(token_a),
    )
    assert empty.status_code == 200
    assert empty.json()["results"] == []


def test_search_by_image_rejects_non_image_upload(client):
    token = _register_seller(client)
    response = client.post(
        "/api/v1/products/search-by-image",
        data={"query": "rice"},
        files={"file": ("notes.txt", b"not an image", "text/plain")},
        headers=_auth(token),
    )
    assert response.status_code == 400


def test_search_by_image_requires_seller(client):
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "buyer@example.com", "password": "password123", "fullName": "Mang Jun", "role": "buyer"},
    )
    buyer_token = response.json()["accessToken"]
    response = client.post(
        "/api/v1/products/search-by-image",
        data={"query": "rice"},
        files={"file": ("photo.jpg", b"fake-bytes", "image/jpeg")},
        headers=_auth(buyer_token),
    )
    assert response.status_code == 403


def _create_measure_product(client, token, **overrides):
    payload = {
        "name": "Cotton Fabric",
        "priceCents": 12000,
        "unitType": "measure",
        "unitLabel": "yd",
        "stockPieces": 50500,
        "lowStockThreshold": 5000,
        "category": "Fabric",
    }
    payload.update(overrides)
    response = client.post("/api/v1/products", json=payload, headers=_auth(token))
    assert response.status_code == 201, response.text
    return response.json()


def test_measure_product_requires_unit_label(client):
    token = _register_seller(client)
    response = client.post(
        "/api/v1/products",
        json={"name": "Fabric", "priceCents": 12000, "unitType": "measure", "unitLabel": "  "},
        headers=_auth(token),
    )
    assert response.status_code == 422


def test_measure_product_rejects_pieces_per_unit(client):
    token = _register_seller(client)
    response = client.post(
        "/api/v1/products",
        json={"name": "Fabric", "priceCents": 12000, "unitType": "measure", "unitLabel": "yd", "piecesPerUnit": 5},
        headers=_auth(token),
    )
    assert response.status_code == 400


def test_non_measure_product_drops_unit_label(client):
    token = _register_seller(client)
    product = _create_bundle_product(client, token, unitLabel="yd")
    assert product["unitLabel"] is None


def test_quick_sell_fractional_measure_prices_per_unit(client):
    token = _register_seller(client)
    product = _create_measure_product(client, token)
    assert product["unitLabel"] == "yd"

    response = client.post(
        f"/api/v1/products/{product['id']}/quick-sell",
        json={"quantity": 1500, "paymentMethod": "cash"},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["totalCents"] == 18000
    assert body["product"]["stockPieces"] == 49000

    sale = client.get(f"/api/v1/sales/{body['saleId']}", headers=_auth(token)).json()
    item = sale["items"][0]
    assert item["unitLabelSnapshot"] == "yd"
    assert item["quantity"] == 1500
    assert item["lineTotalCents"] == 18000

    receipt = client.get(f"/api/v1/sales/receipt/{body['receiptCode']}").json()
    assert receipt["items"][0]["unitLabel"] == "yd"


def test_itemized_measure_sale_rounds_line_total_to_cents(client):
    token = _register_seller(client)
    product = _create_measure_product(client, token, priceCents=1000, unitLabel="m")

    response = client.post(
        "/api/v1/sales",
        json={
            "saleType": "walk_in",
            "paymentMethod": "cash",
            "items": [{"productId": product["id"], "quantity": 333}],
        },
        headers=_auth(token),
    )
    assert response.status_code == 201, response.text
    assert response.json()["totalCents"] == 333


def test_switching_to_measure_without_label_is_rejected(client):
    token = _register_seller(client)
    product = _create_bundle_product(client, token, piecesPerUnit=1, unitType="piece")

    response = client.patch(
        f"/api/v1/products/{product['id']}",
        json={"unitType": "measure"},
        headers=_auth(token),
    )
    assert response.status_code == 400

    response = client.patch(
        f"/api/v1/products/{product['id']}",
        json={"unitType": "measure", "unitLabel": "kg"},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    assert response.json()["unitLabel"] == "kg"
