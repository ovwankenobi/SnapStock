import pytest

from app.config import settings
from test_catalog import _auth, _create_product, _register_seller

PROOF = {"file": ("gcash.png", b"fake-png-bytes", "image/png")}


@pytest.fixture(autouse=True)
def _upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "public"))
    monkeypatch.setattr(settings, "PRIVATE_UPLOAD_DIR", str(tmp_path / "private"))


def _walk_in(client, seller_token, product_id, payment_method="gcash"):
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


def _setup(client):
    seller = _register_seller(client)
    product = _create_product(client, seller, priceCents=1000, stockPieces=10)
    return seller, product


def test_seller_attaches_payment_photo_to_walk_in_sale(client):
    seller, product = _setup(client)
    sale = _walk_in(client, seller, product["id"])

    response = client.post(f"/api/v1/sales/{sale['id']}/proof", files=PROOF, headers=_auth(seller))
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["paymentProofUrl"].startswith("/api/v1/uploads/private/proof_")
    assert body["proofSubmittedAt"] is not None
    assert body["status"] == "completed"

    receipt = client.get(f"/api/v1/sales/receipt/{sale['receiptCode']}").json()
    assert "paymentProofUrl" not in receipt


def test_cash_walk_in_takes_no_payment_photo(client):
    seller, product = _setup(client)
    sale = _walk_in(client, seller, product["id"], payment_method="cash")

    response = client.post(f"/api/v1/sales/{sale['id']}/proof", files=PROOF, headers=_auth(seller))
    assert response.status_code == 409


def test_payment_photo_is_seller_scoped_and_image_only(client):
    seller, product = _setup(client)
    sale = _walk_in(client, seller, product["id"])
    other = _register_seller(client, email="other@example.com", businessName="Other Store")

    stranger = client.post(f"/api/v1/sales/{sale['id']}/proof", files=PROOF, headers=_auth(other))
    assert stranger.status_code == 404

    not_image = client.post(
        f"/api/v1/sales/{sale['id']}/proof",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        headers=_auth(seller),
    )
    assert not_image.status_code == 400


def test_voided_walk_in_takes_no_payment_photo(client):
    seller, product = _setup(client)
    sale = _walk_in(client, seller, product["id"])
    client.post(f"/api/v1/sales/{sale['id']}/void", json={}, headers=_auth(seller))

    response = client.post(f"/api/v1/sales/{sale['id']}/proof", files=PROOF, headers=_auth(seller))
    assert response.status_code == 409
