import pytest

from app.config import settings

BASE = "/api/v1/seller/payout-accounts"


def _register(client, email="seller@example.com", role="seller"):
    payload = {
        "email": email,
        "password": "password123",
        "fullName": "Aling Nena",
        "role": role,
    }
    if role == "seller":
        payload.update(businessName="Nena's Store", businessType="retail")
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text
    return response.json()["accessToken"]


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _create(client, token, **overrides):
    payload = {"method": "gcash", "accountName": "Nena Cruz", "accountNumber": "09171234567"}
    payload.update(overrides)
    return client.post(BASE, json=payload, headers=_auth(token))


@pytest.fixture()
def upload_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "UPLOAD_DIR", str(tmp_path))
    return tmp_path


def test_first_account_becomes_default(client):
    token = _register(client)
    response = _create(client, token)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["method"] == "gcash"
    assert body["accountName"] == "Nena Cruz"
    assert body["isDefault"] is True
    assert body["qrUrl"] is None


def test_switching_default_clears_previous(client):
    token = _register(client)
    gcash = _create(client, token).json()
    maya = _create(client, token, method="maya", isDefault=True).json()
    assert maya["isDefault"] is True

    accounts = client.get(BASE, headers=_auth(token)).json()
    assert [a["id"] for a in accounts] == [maya["id"], gcash["id"]]
    assert [a["isDefault"] for a in accounts] == [True, False]

    response = client.patch(f"{BASE}/{gcash['id']}", json={"isDefault": True}, headers=_auth(token))
    assert response.status_code == 200
    defaults = {a["id"]: a["isDefault"] for a in client.get(BASE, headers=_auth(token)).json()}
    assert defaults == {gcash["id"]: True, maya["id"]: False}


def test_update_fields(client):
    token = _register(client)
    account = _create(client, token).json()
    response = client.patch(
        f"{BASE}/{account['id']}", json={"accountNumber": "09998887777"}, headers=_auth(token)
    )
    assert response.status_code == 200
    assert response.json()["accountNumber"] == "09998887777"


def test_deleting_default_promotes_another(client):
    token = _register(client)
    gcash = _create(client, token).json()
    maya = _create(client, token, method="maya").json()

    assert client.delete(f"{BASE}/{gcash['id']}", headers=_auth(token)).status_code == 204
    accounts = client.get(BASE, headers=_auth(token)).json()
    assert [(a["id"], a["isDefault"]) for a in accounts] == [(maya["id"], True)]


def test_cash_is_rejected(client):
    token = _register(client)
    assert _create(client, token, method="cash").status_code == 422


def test_bank_requires_bank_name(client):
    token = _register(client)
    assert _create(client, token, method="bank_transfer").status_code == 422
    response = _create(client, token, method="bank_transfer", bankName="BDO")
    assert response.status_code == 201
    assert response.json()["bankName"] == "BDO"


def test_switching_to_bank_without_bank_name_is_rejected(client):
    token = _register(client)
    account = _create(client, token).json()
    response = client.patch(
        f"{BASE}/{account['id']}", json={"method": "bank_transfer"}, headers=_auth(token)
    )
    assert response.status_code == 422
    assert client.get(BASE, headers=_auth(token)).json()[0]["method"] == "gcash"


def test_qr_upload(client, upload_dir):
    token = _register(client)
    account = _create(client, token).json()

    response = client.post(
        f"{BASE}/{account['id']}/qr",
        files={"file": ("qr.png", b"\x89PNG fake", "image/png")},
        headers=_auth(token),
    )
    assert response.status_code == 200, response.text
    qr_url = response.json()["qrUrl"]
    assert qr_url.startswith("/uploads/payout_")
    assert (upload_dir / qr_url.removeprefix("/uploads/")).exists()

    rejected = client.post(
        f"{BASE}/{account['id']}/qr",
        files={"file": ("qr.txt", b"hello", "text/plain")},
        headers=_auth(token),
    )
    assert rejected.status_code == 400


def test_seller_cannot_touch_another_sellers_account(client, upload_dir):
    owner = _register(client)
    other = _register(client, email="other@example.com")
    account = _create(client, owner).json()
    url = f"{BASE}/{account['id']}"

    assert client.get(BASE, headers=_auth(other)).json() == []
    assert client.patch(url, json={"accountName": "X"}, headers=_auth(other)).status_code == 404
    assert client.delete(url, headers=_auth(other)).status_code == 404
    qr = client.post(
        f"{url}/qr", files={"file": ("qr.png", b"x", "image/png")}, headers=_auth(other)
    )
    assert qr.status_code == 404
    assert client.get(BASE, headers=_auth(owner)).json()[0]["accountName"] == "Nena Cruz"


def test_buyer_is_forbidden(client):
    token = _register(client, email="buyer@example.com", role="buyer")
    assert client.get(BASE, headers=_auth(token)).status_code == 403
    assert _create(client, token).status_code == 403


def test_accounts_exposed_in_me_and_catalog_seller(client):
    token = _register(client)
    _create(client, token)

    me = client.get("/api/v1/auth/me", headers=_auth(token)).json()
    accounts = me["sellerProfile"]["payoutAccounts"]
    assert [a["method"] for a in accounts] == ["gcash"]

    seller = client.get(f"/api/v1/catalog/sellers/{me['id']}").json()
    assert seller["payoutAccounts"][0]["accountNumber"] == "09171234567"
