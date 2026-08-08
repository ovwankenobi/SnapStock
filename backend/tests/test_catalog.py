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


def _create_product(client, token, **overrides):
    payload = {
        "name": "Pork Belly (Liempo)",
        "priceCents": 32000,
        "unitType": "piece",
        "stockPieces": 50,
        "lowStockThreshold": 10,
        "category": "Pork",
    }
    payload.update(overrides)
    response = client.post("/api/v1/products", json=payload, headers=_auth(token))
    assert response.status_code == 201, response.text
    return response.json()


def test_catalog_lists_only_active_products_from_active_sellers(client):
    seller_token = _register_seller(client)
    active = _create_product(client, seller_token, name="Whole Chicken")
    inactive = _create_product(client, seller_token, name="Chicken Wings")
    client.delete(f"/api/v1/products/{inactive['id']}", headers=_auth(seller_token))

    response = client.get("/api/v1/catalog/products")
    assert response.status_code == 200
    ids = {item["id"] for item in response.json()["items"]}
    assert active["id"] in ids
    assert inactive["id"] not in ids
    assert response.json()["items"][0]["sellerName"] == "Nena's Store"


def test_catalog_search_matches_name_and_category(client):
    seller_token = _register_seller(client)
    _create_product(client, seller_token, name="Beef Brisket", category="Beef")
    _create_product(client, seller_token, name="Ground Pork", category="Pork")

    by_name = client.get("/api/v1/catalog/products", params={"search": "Brisket"}).json()
    assert by_name["total"] == 1

    by_category = client.get("/api/v1/catalog/products", params={"search": "Pork"}).json()
    assert by_category["total"] == 1


def test_get_catalog_product_404_for_unknown_or_inactive(client):
    seller_token = _register_seller(client)
    product = _create_product(client, seller_token)
    client.delete(f"/api/v1/products/{product['id']}", headers=_auth(seller_token))

    response = client.get(f"/api/v1/catalog/products/{product['id']}")
    assert response.status_code == 404


def test_get_catalog_seller_returns_profile_and_products(client):
    seller_token = _register_seller(client)
    product = _create_product(client, seller_token)

    me = client.get("/api/v1/auth/me", headers=_auth(seller_token)).json()
    response = client.get(f"/api/v1/catalog/sellers/{me['id']}")
    assert response.status_code == 200
    body = response.json()
    assert body["businessName"] == "Nena's Store"
    assert [p["id"] for p in body["products"]] == [product["id"]]


def test_get_catalog_seller_404_for_buyer_id(client):
    buyer_token = _register_buyer(client)
    me = client.get("/api/v1/auth/me", headers=_auth(buyer_token)).json()

    response = client.get(f"/api/v1/catalog/sellers/{me['id']}")
    assert response.status_code == 404


def test_search_by_image_returns_keyword_matches_and_never_errors_on_no_results(client):
    seller_token = _register_seller(client)
    _create_product(client, seller_token, name="Whole Chicken", category="Chicken")

    response = client.post(
        "/api/v1/catalog/search-by-image",
        data={"query": "chicken"},
        files={"file": ("photo.jpg", b"fake-bytes", "image/jpeg")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "chicken"
    assert len(body["results"]) == 1
    assert body["results"][0]["confidence"] is None

    empty = client.post(
        "/api/v1/catalog/search-by-image",
        data={"query": "durian"},
        files={"file": ("photo.jpg", b"fake-bytes", "image/jpeg")},
    )
    assert empty.status_code == 200
    assert empty.json()["results"] == []


def test_search_by_image_rejects_non_image_upload(client):
    response = client.post(
        "/api/v1/catalog/search-by-image",
        data={"query": "chicken"},
        files={"file": ("notes.txt", b"not an image", "text/plain")},
    )
    assert response.status_code == 400


def test_buyer_can_buy_a_product_and_stock_is_deducted(client):
    seller_token = _register_seller(client)
    product = _create_product(client, seller_token, stockPieces=50)
    buyer_token = _register_buyer(client)

    response = client.post(
        f"/api/v1/catalog/products/{product['id']}/order",
        json={"quantity": 2, "paymentMethod": "gcash"},
        headers=_auth(buyer_token),
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["saleType"] == "itemized"
    assert body["totalCents"] == 64000
    assert body["items"][0]["quantity"] == 2

    remaining = client.get(f"/api/v1/products/{product['id']}", headers=_auth(seller_token)).json()
    assert remaining["stockPieces"] == 48


def test_buying_more_than_available_stock_is_rejected(client):
    seller_token = _register_seller(client)
    product = _create_product(client, seller_token, stockPieces=1)
    buyer_token = _register_buyer(client)

    response = client.post(
        f"/api/v1/catalog/products/{product['id']}/order",
        json={"quantity": 5, "paymentMethod": "cash"},
        headers=_auth(buyer_token),
    )
    assert response.status_code == 400


def test_my_receipts_lists_only_the_current_buyers_purchases_newest_first(client):
    seller_token = _register_seller(client)
    product = _create_product(client, seller_token, stockPieces=50)

    buyer_a = _register_buyer(client)
    buyer_b = _register_buyer(client, email="buyer-b@example.com", fullName="Ate Marites")

    client.post(
        f"/api/v1/catalog/products/{product['id']}/order",
        json={"quantity": 1, "paymentMethod": "cash"},
        headers=_auth(buyer_a),
    )
    client.post(
        f"/api/v1/catalog/products/{product['id']}/order",
        json={"quantity": 1, "paymentMethod": "cash"},
        headers=_auth(buyer_b),
    )

    response = client.get("/api/v1/me/receipts", headers=_auth(buyer_a))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["sellerName"] == "Nena's Store"


def test_my_receipts_requires_buyer_role(client):
    seller_token = _register_seller(client)
    response = client.get("/api/v1/me/receipts", headers=_auth(seller_token))
    assert response.status_code == 403
