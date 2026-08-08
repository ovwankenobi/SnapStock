import uuid

from fastapi import Depends

from app.core.deps import require_seller
from app.core.security import create_access_token


def _register(client, **overrides):
    payload = {
        "email": "seller@example.com",
        "password": "password123",
        "fullName": "Aling Nena",
        "role": "seller",
        "businessName": "Nena's Store",
        "businessType": "retail",
    }
    payload.update(overrides)
    return client.post("/api/v1/auth/register", json=payload)


def test_register_seller_and_login(client):
    response = _register(client)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["user"]["role"] == "seller"
    assert body["user"]["email"] == "seller@example.com"
    assert body["tokenType"] == "bearer"
    assert body["accessToken"]

    login = client.post(
        "/api/v1/auth/login",
        data={"username": "seller@example.com", "password": "password123"},
    )
    assert login.status_code == 200
    assert login.json()["user"]["email"] == "seller@example.com"


def test_register_seller_requires_business_fields(client):
    response = _register(client, businessName=None, businessType=None)
    assert response.status_code == 422


def test_register_buyer_needs_no_business_fields(client):
    response = _register(
        client,
        email="buyer@example.com",
        role="buyer",
        businessName=None,
        businessType=None,
    )
    assert response.status_code == 201
    assert response.json()["user"]["role"] == "buyer"


def test_register_duplicate_email_rejected(client):
    assert _register(client).status_code == 201
    duplicate = _register(client, fullName="Someone Else")
    assert duplicate.status_code == 400


def test_login_wrong_password_rejected(client):
    _register(client)
    response = client.post(
        "/api/v1/auth/login", data={"username": "seller@example.com", "password": "wrong"}
    )
    assert response.status_code == 401


def test_me_requires_auth(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_get_and_patch(client):
    token = _register(client).json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    me = client.get("/api/v1/auth/me", headers=headers)
    assert me.status_code == 200
    assert me.json()["email"] == "seller@example.com"
    assert me.json()["sellerProfile"]["businessName"] == "Nena's Store"

    updated = client.patch(
        "/api/v1/auth/me",
        headers=headers,
        json={"phone": "09170000000", "preferredLanguage": "tl", "businessName": "New Name"},
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["phone"] == "09170000000"
    assert body["preferredLanguage"] == "tl"
    assert body["sellerProfile"]["businessName"] == "New Name"


def test_expired_token_rejected(client):
    token = create_access_token(subject=str(uuid.uuid4()), role="seller", expires_minutes=-1)
    response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


def test_garbage_token_rejected(client):
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401


def test_seller_only_route_allows_seller_and_blocks_buyer(client):
    @client.app.get("/api/v1/_test/seller-only")
    def seller_only_probe(user=Depends(require_seller)):
        return {"ok": True}

    seller_token = _register(client).json()["accessToken"]
    buyer_token = _register(
        client, email="buyer2@example.com", role="buyer", businessName=None, businessType=None
    ).json()["accessToken"]

    seller_response = client.get(
        "/api/v1/_test/seller-only", headers={"Authorization": f"Bearer {seller_token}"}
    )
    buyer_response = client.get(
        "/api/v1/_test/seller-only", headers={"Authorization": f"Bearer {buyer_token}"}
    )

    assert seller_response.status_code == 200
    assert buyer_response.status_code == 403
