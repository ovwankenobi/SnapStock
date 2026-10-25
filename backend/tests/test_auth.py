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


# --- password reset ---------------------------------------------------------------------------

import re  # noqa: E402
from urllib.parse import unquote  # noqa: E402

import pytest  # noqa: E402

from app.core.security import create_password_reset_token  # noqa: E402
from app.services import email as email_service  # noqa: E402


@pytest.fixture()
def sent_emails(monkeypatch):
    sent = []
    monkeypatch.setattr(email_service, "send_email", lambda to, subject, body: sent.append((to, subject, body)))
    return sent


def _token_from(body):
    match = re.search(r"/reset-password\?token=(\S+)", body)
    assert match, body
    return unquote(match.group(1))


def _login(client, password):
    return client.post(
        "/api/v1/auth/login", data={"username": "seller@example.com", "password": password}
    )


def test_forgot_password_unknown_email_sends_nothing(client, sent_emails):
    response = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert response.status_code == 202
    assert sent_emails == []


def test_forgot_password_same_response_for_known_email(client, sent_emails):
    _register(client)
    known = client.post("/api/v1/auth/forgot-password", json={"email": "seller@example.com"})
    unknown = client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    assert known.status_code == unknown.status_code == 202
    assert known.json() == unknown.json()
    assert len(sent_emails) == 1
    to, _subject, body = sent_emails[0]
    assert to == "seller@example.com"
    assert "http://localhost:5173/reset-password?token=" in body


def test_reset_password_flow_and_single_use(client, sent_emails):
    _register(client)
    client.post("/api/v1/auth/forgot-password", json={"email": "seller@example.com"})
    token = _token_from(sent_emails[0][2])

    response = client.post(
        "/api/v1/auth/reset-password", json={"token": token, "newPassword": "brandnew456"}
    )
    assert response.status_code == 204, response.text
    assert _login(client, "brandnew456").status_code == 200
    assert _login(client, "password123").status_code == 401

    reused = client.post(
        "/api/v1/auth/reset-password", json={"token": token, "newPassword": "another789"}
    )
    assert reused.status_code == 400
    assert _login(client, "brandnew456").status_code == 200


def test_reset_password_expired_token_rejected(client):
    body = _register(client).json()
    from app.database import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        user = db.get(User, uuid.UUID(body["user"]["id"]))
        token = create_password_reset_token(str(user.id), user.hashed_password, expires_minutes=-1)
    finally:
        db.close()

    response = client.post(
        "/api/v1/auth/reset-password", json={"token": token, "newPassword": "brandnew456"}
    )
    assert response.status_code == 400


def test_reset_password_rejects_access_token(client):
    access_token = _register(client).json()["accessToken"]
    response = client.post(
        "/api/v1/auth/reset-password", json={"token": access_token, "newPassword": "brandnew456"}
    )
    assert response.status_code == 400


def test_reset_password_rejects_garbage_token(client):
    response = client.post(
        "/api/v1/auth/reset-password", json={"token": "not-a-token", "newPassword": "brandnew456"}
    )
    assert response.status_code == 400


def test_reset_password_requires_min_length(client, sent_emails):
    _register(client)
    client.post("/api/v1/auth/forgot-password", json={"email": "seller@example.com"})
    token = _token_from(sent_emails[0][2])
    response = client.post("/api/v1/auth/reset-password", json={"token": token, "newPassword": "short"})
    assert response.status_code == 422


def test_reset_email_uses_preferred_language(client, sent_emails):
    token = _register(client).json()["accessToken"]
    client.patch(
        "/api/v1/auth/me", json={"preferredLanguage": "tl"}, headers={"Authorization": f"Bearer {token}"}
    )
    client.post("/api/v1/auth/forgot-password", json={"email": "seller@example.com"})
    assert sent_emails[0][1] == "I-reset ang iyong SnapStock password"


# --- change password --------------------------------------------------------------------------


def test_change_password_emails_link_to_own_address(client, sent_emails):
    token = _register(client).json()["accessToken"]
    response = client.post(
        "/api/v1/auth/change-password", headers={"Authorization": f"Bearer {token}"}
    )
    assert response.status_code == 202
    assert len(sent_emails) == 1
    to, _subject, body = sent_emails[0]
    assert to == "seller@example.com"

    reset_token = _token_from(body)
    response = client.post(
        "/api/v1/auth/reset-password", json={"token": reset_token, "newPassword": "brandnew456"}
    )
    assert response.status_code == 204
    assert _login(client, "brandnew456").status_code == 200
    assert _login(client, "password123").status_code == 401


def test_change_password_requires_auth(client, sent_emails):
    assert client.post("/api/v1/auth/change-password").status_code == 401
    assert sent_emails == []


# --- QR login ---------------------------------------------------------------------------------


def _auth(token):
    return {"Authorization": f"Bearer {token}"}


def _issue_qr(client, token, password="password123"):
    return client.post("/api/v1/auth/qr-login-key", json={"currentPassword": password}, headers=_auth(token))


def _qr_login(client, key):
    return client.post("/api/v1/auth/qr-login", json={"key": key})


def test_qr_login_flow(client):
    token = _register(client).json()["accessToken"]
    issued = _issue_qr(client, token)
    assert issued.status_code == 201, issued.text
    key = issued.json()["key"]
    assert key.startswith("ssqr1_")

    me = client.get("/api/v1/auth/me", headers=_auth(token)).json()
    assert me["qrLoginCreatedAt"] is not None

    login = _qr_login(client, key)
    assert login.status_code == 200, login.text
    new_token = login.json()["accessToken"]
    assert client.get("/api/v1/auth/me", headers=_auth(new_token)).json()["email"] == "seller@example.com"


def test_qr_login_key_requires_correct_password(client):
    token = _register(client).json()["accessToken"]
    assert _issue_qr(client, token, password="wrong").status_code == 400
    assert client.post("/api/v1/auth/qr-login-key", json={"currentPassword": "password123"}).status_code == 401


def test_qr_login_regenerate_invalidates_old_key(client):
    token = _register(client).json()["accessToken"]
    old_key = _issue_qr(client, token).json()["key"]
    new_key = _issue_qr(client, token).json()["key"]
    assert _qr_login(client, old_key).status_code == 401
    assert _qr_login(client, new_key).status_code == 200


def test_qr_login_revoked_key_rejected(client):
    token = _register(client).json()["accessToken"]
    key = _issue_qr(client, token).json()["key"]
    assert client.delete("/api/v1/auth/qr-login-key", headers=_auth(token)).status_code == 204
    assert _qr_login(client, key).status_code == 401
    assert client.get("/api/v1/auth/me", headers=_auth(token)).json()["qrLoginCreatedAt"] is None


def test_qr_login_inactive_user_rejected(client):
    body = _register(client).json()
    key = _issue_qr(client, body["accessToken"]).json()["key"]
    from app.database import SessionLocal
    from app.models import User

    db = SessionLocal()
    try:
        db.get(User, uuid.UUID(body["user"]["id"])).is_active = False
        db.commit()
    finally:
        db.close()
    assert _qr_login(client, key).status_code == 401


def test_qr_login_garbage_key_rejected(client):
    _register(client)
    assert _qr_login(client, "not-a-login-qr").status_code == 401
    assert _qr_login(client, "ssqr1_made-up").status_code == 401


def test_qr_login_survives_password_reset(client, sent_emails):
    token = _register(client).json()["accessToken"]
    key = _issue_qr(client, token).json()["key"]
    client.post("/api/v1/auth/forgot-password", json={"email": "seller@example.com"})
    reset_token = _token_from(sent_emails[0][2])
    assert client.post(
        "/api/v1/auth/reset-password", json={"token": reset_token, "newPassword": "brandnew456"}
    ).status_code == 204
    assert _qr_login(client, key).status_code == 200
