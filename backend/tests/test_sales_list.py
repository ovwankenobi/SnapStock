from test_catalog import _auth, _create_product, _register_seller


def _walk_in(client, seller_token, product_id, payment_method):
    response = client.post(
        "/api/v1/sales",
        json={
            "saleType": "walk_in",
            "paymentMethod": payment_method,
            "items": [{"productId": product_id, "quantity": 1}],
        },
        headers=_auth(seller_token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _list(client, seller_token, **params):
    response = client.get("/api/v1/sales", params=params, headers=_auth(seller_token))
    assert response.status_code == 200, response.text
    return response.json()


def test_list_sales_filters_by_payment_method(client):
    seller = _register_seller(client)
    product = _create_product(client, seller, priceCents=1000, stockPieces=10)
    cash = _walk_in(client, seller, product["id"], "cash")
    gcash = _walk_in(client, seller, product["id"], "gcash")

    gcash_only = _list(client, seller, payment_method="gcash")
    assert gcash_only["total"] == 1
    assert [s["id"] for s in gcash_only["items"]] == [gcash["id"]]

    cash_walk_ins = _list(client, seller, sale_type="walk_in", payment_method="cash")
    assert [s["id"] for s in cash_walk_ins["items"]] == [cash["id"]]

    assert _list(client, seller, sale_type="itemized", payment_method="cash")["total"] == 0
    assert _list(client, seller)["total"] == 2


def test_list_sales_rejects_unknown_payment_method(client):
    seller = _register_seller(client)
    response = client.get("/api/v1/sales", params={"payment_method": "bitcoin"}, headers=_auth(seller))
    assert response.status_code == 422
