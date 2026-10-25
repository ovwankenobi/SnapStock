import pytest

from app.config import settings
from app.database import SessionLocal
from app.models import StockMovement
from test_catalog import _auth, _create_product, _register_buyer, _register_seller

PROOF = {"file": ("gcash.png", b"fake-png-bytes", "image/png")}


@pytest.fixture(autouse=True)
def _upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path / "public"))
    monkeypatch.setattr(settings, "PRIVATE_UPLOAD_DIR", str(tmp_path / "private"))


def _order(client, buyer_token, product_id, quantity=2, payment_method="gcash"):
    response = client.post(
        f"/api/v1/catalog/products/{product_id}/order",
        json={"quantity": quantity, "paymentMethod": payment_method},
        headers=_auth(buyer_token),
    )
    assert response.status_code == 201, response.text
    return response.json()


def _stock(client, seller_token, product_id):
    return client.get(f"/api/v1/products/{product_id}", headers=_auth(seller_token)).json()["stockPieces"]


def _summary(client, seller_token):
    return client.get("/api/v1/analytics/summary", headers=_auth(seller_token)).json()


def _setup(client):
    seller = _register_seller(client)
    buyer = _register_buyer(client)
    product = _create_product(client, seller, priceCents=1000, stockPieces=10)
    return seller, buyer, product


def test_buyer_order_reserves_stock_but_does_not_count_until_confirmed(client):
    seller, buyer, product = _setup(client)

    sale = _order(client, buyer, product["id"])
    assert sale["status"] == "pending_payment"
    assert sale["saleType"] == "itemized"
    assert sale["buyerId"] is not None
    assert _stock(client, seller, product["id"]) == 8

    summary = _summary(client, seller)
    assert summary["todaySaleCount"] == 0
    assert summary["todayRevenueCents"] == 0

    pending = client.get(
        "/api/v1/sales", params={"status": "pending_payment"}, headers=_auth(seller)
    ).json()
    assert [s["id"] for s in pending["items"]] == [sale["id"]]


def test_digital_order_needs_proof_then_confirm_counts_it_for_the_buyer(client):
    seller, buyer, product = _setup(client)
    sale = _order(client, buyer, product["id"])

    early = client.post(f"/api/v1/sales/{sale['id']}/confirm-payment", headers=_auth(seller))
    assert early.status_code == 409

    upload = client.post(f"/api/v1/me/orders/{sale['id']}/proof", files=PROOF, headers=_auth(buyer))
    assert upload.status_code == 200, upload.text
    order = upload.json()
    assert order["paymentProofUrl"].startswith("/api/v1/uploads/private/proof_")
    assert order["proofSubmittedAt"] is not None
    assert order["sellerName"] == "Nena's Store"

    seller_view = client.get(f"/api/v1/sales/{sale['id']}", headers=_auth(seller)).json()
    assert seller_view["paymentProofUrl"] == order["paymentProofUrl"]

    confirmed = client.post(f"/api/v1/sales/{sale['id']}/confirm-payment", headers=_auth(seller))
    assert confirmed.status_code == 200, confirmed.text
    body = confirmed.json()
    assert body["status"] == "completed"
    assert body["buyerName"] == "Mang Jun"

    summary = _summary(client, seller)
    assert summary["todaySaleCount"] == 1
    assert summary["todayRevenueCents"] == 2000
    assert _stock(client, seller, product["id"]) == 8

    again = client.post(f"/api/v1/sales/{sale['id']}/confirm-payment", headers=_auth(seller))
    assert again.status_code == 409
    late_proof = client.post(f"/api/v1/me/orders/{sale['id']}/proof", files=PROOF, headers=_auth(buyer))
    assert late_proof.status_code == 409


def test_cash_order_is_confirmed_without_proof(client):
    seller, buyer, product = _setup(client)
    sale = _order(client, buyer, product["id"], payment_method="cash")

    upload = client.post(f"/api/v1/me/orders/{sale['id']}/proof", files=PROOF, headers=_auth(buyer))
    assert upload.status_code == 409

    confirmed = client.post(f"/api/v1/sales/{sale['id']}/confirm-payment", headers=_auth(seller))
    assert confirmed.status_code == 200, confirmed.text
    assert confirmed.json()["status"] == "completed"


def test_proof_upload_is_buyer_scoped_and_image_only(client):
    seller, buyer, product = _setup(client)
    sale = _order(client, buyer, product["id"])
    other_buyer = _register_buyer(client, email="other@example.com", fullName="Ate Marites")

    stranger = client.post(f"/api/v1/me/orders/{sale['id']}/proof", files=PROOF, headers=_auth(other_buyer))
    assert stranger.status_code == 404
    assert client.get(f"/api/v1/me/orders/{sale['id']}", headers=_auth(other_buyer)).status_code == 404

    not_image = client.post(
        f"/api/v1/me/orders/{sale['id']}/proof",
        files={"file": ("notes.txt", b"hello", "text/plain")},
        headers=_auth(buyer),
    )
    assert not_image.status_code == 400


@pytest.mark.parametrize("who", ["seller", "buyer"])
def test_rejected_or_cancelled_order_returns_stock_and_never_counts(client, who):
    seller, buyer, product = _setup(client)
    sale = _order(client, buyer, product["id"])

    if who == "seller":
        response = client.post(
            f"/api/v1/sales/{sale['id']}/reject", json={"reason": "No payment received"}, headers=_auth(seller)
        )
    else:
        response = client.post(f"/api/v1/me/orders/{sale['id']}/cancel", headers=_auth(buyer))
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"
    assert _stock(client, seller, product["id"]) == 10

    with SessionLocal() as db:
        reasons = [m.reason.value for m in db.query(StockMovement).filter(StockMovement.product_id == product["id"])]
    assert "cancel" in reasons

    assert _summary(client, seller)["todaySaleCount"] == 0
    assert client.post(f"/api/v1/me/orders/{sale['id']}/cancel", headers=_auth(buyer)).status_code == 409
    assert client.post(f"/api/v1/sales/{sale['id']}/confirm-payment", headers=_auth(seller)).status_code == 409


def test_pending_order_cannot_be_voided_or_refunded(client):
    seller, buyer, product = _setup(client)
    sale = _order(client, buyer, product["id"])

    for action in ("void", "refund"):
        response = client.post(f"/api/v1/sales/{sale['id']}/{action}", json={}, headers=_auth(seller))
        assert response.status_code == 409


def test_public_receipt_never_exposes_the_payment_proof(client):
    seller, buyer, product = _setup(client)
    sale = _order(client, buyer, product["id"])
    client.post(f"/api/v1/me/orders/{sale['id']}/proof", files=PROOF, headers=_auth(buyer))

    receipt = client.get(f"/api/v1/sales/receipt/{sale['receiptCode']}").json()
    assert receipt["status"] == "pending_payment"
    assert "paymentProofUrl" not in receipt


def test_my_receipts_show_the_order_status(client):
    seller, buyer, product = _setup(client)
    _order(client, buyer, product["id"])

    receipts = client.get("/api/v1/me/receipts", headers=_auth(buyer)).json()
    assert receipts["items"][0]["status"] == "pending_payment"


def _seller_thread(client, seller_token):
    conversations = client.get("/api/v1/conversations", headers=_auth(seller_token)).json()["items"]
    assert len(conversations) == 1
    conversation = conversations[0]
    messages = client.get(
        f"/api/v1/conversations/{conversation['id']}/messages", headers=_auth(seller_token)
    ).json()["items"]
    return conversation, messages


def test_cash_order_posts_an_order_card_to_the_seller(client):
    seller, buyer, product = _setup(client)
    sale = _order(client, buyer, product["id"], payment_method="cash")

    conversation, messages = _seller_thread(client, seller)
    assert conversation["unreadCount"] == 1
    assert conversation["product"]["id"] == product["id"]
    [card] = messages
    assert card["saleId"] == sale["id"]
    assert "approve or not" in card["body"].lower()
    assert card["order"]["status"] == "pending_payment"
    assert card["order"]["paymentMethod"] == "cash"
    assert card["order"]["totalCents"] == sale["totalCents"]


def test_digital_order_card_waits_for_proof_and_tracks_status(client):
    seller, buyer, product = _setup(client)
    sale = _order(client, buyer, product["id"])
    assert client.get("/api/v1/conversations", headers=_auth(seller)).json()["items"] == []

    client.post(f"/api/v1/me/orders/{sale['id']}/proof", files=PROOF, headers=_auth(buyer))
    _, [card] = _seller_thread(client, seller)
    assert "proof of payment" in card["body"]
    assert card["order"]["paymentProofUrl"]

    client.post(f"/api/v1/sales/{sale['id']}/confirm-payment", headers=_auth(seller))
    _, [card] = _seller_thread(client, seller)
    assert card["order"]["status"] == "completed"


def test_plain_messages_have_no_order(client):
    seller, buyer, _ = _setup(client)
    seller_id = client.get("/api/v1/auth/me", headers=_auth(seller)).json()["id"]
    conversation = client.post(
        "/api/v1/conversations", json={"otherUserId": seller_id}, headers=_auth(buyer)
    ).json()
    client.post(f"/api/v1/conversations/{conversation['id']}/messages", json={"body": "hi"}, headers=_auth(buyer))
    _, [message] = _seller_thread(client, seller)
    assert message["saleId"] is None and message["order"] is None


def test_payment_proof_is_private_and_served_only_by_signed_link(client, tmp_path):
    _, buyer, product = _setup(client)
    sale = _order(client, buyer, product["id"])
    url = client.post(f"/api/v1/me/orders/{sale['id']}/proof", files=PROOF, headers=_auth(buyer)).json()[
        "paymentProofUrl"
    ]

    # Stored outside the publicly served upload directory.
    filename = url.split("?")[0].rsplit("/", 1)[1]
    assert (tmp_path / "private" / filename).exists()
    assert client.get(f"/uploads/{filename}").status_code == 404

    signed = client.get(url)
    assert signed.status_code == 200
    assert signed.content == PROOF["file"][1]

    tampered = client.get(url.replace("signature=", "signature=0"))
    assert tampered.status_code == 403
    expired = client.get(url.split("?")[0], params={"expires": 1, "signature": "x"})
    assert expired.status_code == 403


def test_oversized_upload_is_rejected(client, monkeypatch):
    _, buyer, product = _setup(client)
    sale = _order(client, buyer, product["id"])
    monkeypatch.setattr(settings, "MAX_UPLOAD_BYTES", 4)

    response = client.post(f"/api/v1/me/orders/{sale['id']}/proof", files=PROOF, headers=_auth(buyer))
    assert response.status_code == 400
    assert "MB or smaller" in response.json()["detail"]
