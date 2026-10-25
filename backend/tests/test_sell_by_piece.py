from app.services.inventory import per_piece_cents
from test_catalog import _register_buyer
from test_inventory import _auth, _create_bundle_product, _register_seller


def _walk_in(client, token, items):
    return client.post(
        "/api/v1/sales",
        json={"saleType": "walk_in", "paymentMethod": "cash", "items": items},
        headers=_auth(token),
    )


def _stock(client, token, product_id):
    return client.get(f"/api/v1/products/{product_id}", headers=_auth(token)).json()["stockPieces"]


def test_per_piece_price_rounds_half_up():
    assert per_piece_cents(10000, 3) == 3333
    assert per_piece_cents(5000, 10) == 500
    assert per_piece_cents(5, 2) == 3


def test_walk_in_sale_by_piece_deducts_pieces_and_snapshots_a_piece_line(client):
    token = _register_seller(client)
    product = _create_bundle_product(client, token, priceCents=5000, costCents=3000, stockPieces=100)

    response = _walk_in(client, token, [{"productId": product["id"], "quantity": 3, "byPiece": True}])
    assert response.status_code == 201, response.text
    item = response.json()["items"][0]

    assert item["unitTypeSnapshot"] == "piece"
    assert item["listPriceCentsSnapshot"] == 500
    assert item["unitPriceCentsSnapshot"] == 500
    assert item["piecesDeducted"] == 3
    assert item["lineTotalCents"] == 1500
    assert response.json()["totalCents"] == 1500
    assert _stock(client, token, product["id"]) == 97


def test_bundle_and_piece_lines_of_one_product_are_validated_together(client):
    token = _register_seller(client)
    short = _create_bundle_product(client, token, name="Eggs 12", priceCents=5000, stockPieces=12)
    enough = _create_bundle_product(client, token, name="Eggs 13", priceCents=5000, stockPieces=13)

    def lines(product_id):
        return [
            {"productId": product_id, "quantity": 1},
            {"productId": product_id, "quantity": 3, "byPiece": True},
        ]

    assert _walk_in(client, token, lines(short["id"])).status_code == 400
    assert _stock(client, token, short["id"]) == 12

    response = _walk_in(client, token, lines(enough["id"]))
    assert response.status_code == 201, response.text
    assert response.json()["totalCents"] == 5000 + 1500
    assert _stock(client, token, enough["id"]) == 0


def test_by_piece_on_a_non_bundle_product_is_rejected(client):
    token = _register_seller(client)
    product = _create_bundle_product(client, token, unitType="piece", piecesPerUnit=1, stockPieces=10)

    response = _walk_in(client, token, [{"productId": product["id"], "quantity": 1, "byPiece": True}])
    assert response.status_code == 400
    assert _stock(client, token, product["id"]) == 10


def test_buyer_order_by_piece_reserves_pieces_and_cancel_returns_them(client):
    seller = _register_seller(client)
    buyer = _register_buyer(client)
    product = _create_bundle_product(client, seller, priceCents=5000, stockPieces=20)

    response = client.post(
        f"/api/v1/catalog/products/{product['id']}/order",
        json={"quantity": 2, "paymentMethod": "cash", "byPiece": True},
        headers=_auth(buyer),
    )
    assert response.status_code == 201, response.text
    sale = response.json()
    assert sale["totalCents"] == 1000
    assert _stock(client, seller, product["id"]) == 18

    cancel = client.post(f"/api/v1/me/orders/{sale['id']}/cancel", headers=_auth(buyer))
    assert cancel.status_code == 200, cancel.text
    assert _stock(client, seller, product["id"]) == 20
