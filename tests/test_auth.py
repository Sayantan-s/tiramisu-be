def test_request_otp_returns_request_id(client):
    r = client.post("/auth/request-otp", json={"phone": "9999900001"})
    assert r.status_code == 200
    body = r.json()
    assert "request_id" in body and len(body["request_id"]) > 0


def test_verify_otp_with_dev_code_creates_user_and_returns_token(client):
    r = client.post("/auth/request-otp", json={"phone": "9999900001"})
    assert r.status_code == 200

    r = client.post(
        "/auth/verify-otp",
        json={"phone": "9999900001", "otp": "123456", "name": "Alice"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["access_token"]
    assert body["user"]["phone"] == "9999900001"
    assert body["user"]["name"] == "Alice"


def test_verify_otp_with_wrong_code_rejected(client):
    client.post("/auth/request-otp", json={"phone": "9999900001"})
    r = client.post("/auth/verify-otp", json={"phone": "9999900001", "otp": "000000"})
    assert r.status_code == 401


def test_otp_is_single_use(client):
    client.post("/auth/request-otp", json={"phone": "9999900001"})
    r = client.post("/auth/verify-otp", json={"phone": "9999900001", "otp": "123456"})
    assert r.status_code == 200
    r = client.post("/auth/verify-otp", json={"phone": "9999900001", "otp": "123456"})
    assert r.status_code == 401


def test_existing_user_signs_in_without_creating_duplicate(client):
    client.post("/auth/request-otp", json={"phone": "9999900001"})
    r1 = client.post(
        "/auth/verify-otp", json={"phone": "9999900001", "otp": "123456", "name": "Alice"}
    )
    user_id_1 = r1.json()["user"]["id"]

    client.post("/auth/request-otp", json={"phone": "9999900001"})
    r2 = client.post("/auth/verify-otp", json={"phone": "9999900001", "otp": "123456"})
    assert r2.json()["user"]["id"] == user_id_1


def test_me_requires_auth(client):
    r = client.get("/me")
    assert r.status_code == 401


def test_me_returns_current_user(client):
    client.post("/auth/request-otp", json={"phone": "9999900002"})
    token = client.post(
        "/auth/verify-otp", json={"phone": "9999900002", "otp": "123456", "name": "Bob"}
    ).json()["access_token"]

    r = client.get("/me", headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 200
    assert r.json()["name"] == "Bob"


def test_patch_me_updates_name(client):
    client.post("/auth/request-otp", json={"phone": "9999900002"})
    token = client.post(
        "/auth/verify-otp", json={"phone": "9999900002", "otp": "123456"}
    ).json()["access_token"]

    r = client.patch(
        "/me", headers={"Authorization": f"Bearer {token}"}, json={"name": "Bobby"}
    )
    assert r.status_code == 200
    assert r.json()["name"] == "Bobby"
