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


def _me(client, token):
    return client.get("/api/v1/auth/me", headers=_auth(token)).json()


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


def test_buyer_can_start_a_conversation_with_a_seller(client):
    seller_token = _register_seller(client)
    seller = _me(client, seller_token)
    buyer_token = _register_buyer(client)

    response = client.post(
        "/api/v1/conversations", json={"otherUserId": seller["id"]}, headers=_auth(buyer_token)
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["otherUser"]["id"] == seller["id"]
    assert body["product"] is None
    assert body["unreadCount"] == 0


def test_creating_a_conversation_is_idempotent(client):
    seller_token = _register_seller(client)
    seller = _me(client, seller_token)
    buyer_token = _register_buyer(client)

    first = client.post(
        "/api/v1/conversations", json={"otherUserId": seller["id"]}, headers=_auth(buyer_token)
    ).json()
    second = client.post(
        "/api/v1/conversations", json={"otherUserId": seller["id"]}, headers=_auth(buyer_token)
    ).json()
    assert first["id"] == second["id"]


def test_conversation_scoped_to_a_product_is_distinct_from_general_conversation(client):
    seller_token = _register_seller(client)
    seller = _me(client, seller_token)
    product = _create_product(client, seller_token)
    buyer_token = _register_buyer(client)

    general = client.post(
        "/api/v1/conversations", json={"otherUserId": seller["id"]}, headers=_auth(buyer_token)
    ).json()
    about_product = client.post(
        "/api/v1/conversations",
        json={"otherUserId": seller["id"], "productId": product["id"]},
        headers=_auth(buyer_token),
    ).json()

    assert general["id"] != about_product["id"]
    assert about_product["product"]["id"] == product["id"]


def test_seller_can_start_conversation_with_a_buyer(client):
    seller_token = _register_seller(client)
    buyer_token = _register_buyer(client)
    buyer = _me(client, buyer_token)

    response = client.post(
        "/api/v1/conversations", json={"otherUserId": buyer["id"]}, headers=_auth(seller_token)
    )
    assert response.status_code == 201, response.text
    assert response.json()["otherUser"]["id"] == buyer["id"]


def test_create_conversation_404_for_unknown_user(client):
    buyer_token = _register_buyer(client)
    response = client.post(
        "/api/v1/conversations",
        json={"otherUserId": "00000000-0000-0000-0000-000000000000"},
        headers=_auth(buyer_token),
    )
    assert response.status_code == 404


def test_create_conversation_404_when_product_belongs_to_a_different_seller(client):
    seller_a_token = _register_seller(client)
    product_a = _create_product(client, seller_a_token)

    seller_b_token = _register_seller(client, email="seller-b@example.com", businessName="Other Store")
    seller_b = _me(client, seller_b_token)

    buyer_token = _register_buyer(client)
    response = client.post(
        "/api/v1/conversations",
        json={"otherUserId": seller_b["id"], "productId": product_a["id"]},
        headers=_auth(buyer_token),
    )
    assert response.status_code == 404


def test_messages_send_and_list_newest_first(client):
    seller_token = _register_seller(client)
    seller = _me(client, seller_token)
    buyer_token = _register_buyer(client)

    conversation = client.post(
        "/api/v1/conversations", json={"otherUserId": seller["id"]}, headers=_auth(buyer_token)
    ).json()
    conv_id = conversation["id"]

    client.post(
        f"/api/v1/conversations/{conv_id}/messages", json={"body": "Meron pa po bang liempo?"}, headers=_auth(buyer_token)
    )
    client.post(
        f"/api/v1/conversations/{conv_id}/messages", json={"body": "Meron pa po, 3kg natitira."}, headers=_auth(seller_token)
    )

    response = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=_auth(buyer_token))
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert body["items"][0]["body"] == "Meron pa po, 3kg natitira."
    assert body["items"][1]["body"] == "Meron pa po bang liempo?"


def test_sending_a_message_updates_conversation_last_message_at_and_ordering(client):
    seller_token = _register_seller(client)
    seller = _me(client, seller_token)
    buyer_a = _register_buyer(client)
    buyer_b_token = _register_buyer(client, email="buyer-b@example.com", fullName="Ate Marites")
    buyer_b = _me(client, buyer_b_token)

    conv_a = client.post(
        "/api/v1/conversations", json={"otherUserId": seller["id"]}, headers=_auth(buyer_a)
    ).json()
    conv_b = client.post(
        "/api/v1/conversations", json={"otherUserId": seller["id"]}, headers=_auth(buyer_b_token)
    ).json()

    client.post(
        f"/api/v1/conversations/{conv_a['id']}/messages", json={"body": "hi"}, headers=_auth(buyer_a)
    )
    client.post(
        f"/api/v1/conversations/{conv_b['id']}/messages", json={"body": "hello"}, headers=_auth(buyer_b_token)
    )

    listing = client.get("/api/v1/conversations", headers=_auth(seller_token)).json()
    assert [c["id"] for c in listing["items"]] == [conv_b["id"], conv_a["id"]]
    assert listing["items"][0]["lastMessagePreview"] == "hello"
    assert listing["items"][0]["unreadCount"] == 1


def test_mark_read_clears_unread_count_for_the_reader_only(client):
    seller_token = _register_seller(client)
    seller = _me(client, seller_token)
    buyer_token = _register_buyer(client)

    conversation = client.post(
        "/api/v1/conversations", json={"otherUserId": seller["id"]}, headers=_auth(buyer_token)
    ).json()
    conv_id = conversation["id"]
    client.post(f"/api/v1/conversations/{conv_id}/messages", json={"body": "hi"}, headers=_auth(buyer_token))

    mark = client.post(f"/api/v1/conversations/{conv_id}/read", headers=_auth(seller_token))
    assert mark.status_code == 204

    seller_view = client.get("/api/v1/conversations", headers=_auth(seller_token)).json()
    assert seller_view["items"][0]["unreadCount"] == 0

    buyer_view = client.get("/api/v1/conversations", headers=_auth(buyer_token)).json()
    assert buyer_view["items"][0]["unreadCount"] == 0  # buyer sent it, nothing unread for buyer either


def test_non_participant_cannot_read_or_post_to_a_conversation(client):
    seller_token = _register_seller(client)
    seller = _me(client, seller_token)
    buyer_token = _register_buyer(client)
    outsider_token = _register_buyer(client, email="outsider@example.com", fullName="Outsider")

    conversation = client.post(
        "/api/v1/conversations", json={"otherUserId": seller["id"]}, headers=_auth(buyer_token)
    ).json()
    conv_id = conversation["id"]

    get_messages = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=_auth(outsider_token))
    assert get_messages.status_code == 404

    send = client.post(
        f"/api/v1/conversations/{conv_id}/messages", json={"body": "snooping"}, headers=_auth(outsider_token)
    )
    assert send.status_code == 404

    mark = client.post(f"/api/v1/conversations/{conv_id}/read", headers=_auth(outsider_token))
    assert mark.status_code == 404


def test_list_conversations_only_returns_the_current_users_conversations(client):
    seller_token = _register_seller(client)
    seller = _me(client, seller_token)
    buyer_a = _register_buyer(client)
    buyer_b_token = _register_buyer(client, email="buyer-b@example.com", fullName="Ate Marites")

    client.post("/api/v1/conversations", json={"otherUserId": seller["id"]}, headers=_auth(buyer_a))
    client.post("/api/v1/conversations", json={"otherUserId": seller["id"]}, headers=_auth(buyer_b_token))

    buyer_a_view = client.get("/api/v1/conversations", headers=_auth(buyer_a)).json()
    assert len(buyer_a_view["items"]) == 1
