from fastapi.testclient import TestClient


def sign_in(client: TestClient, phone: str, name: str | None = None) -> tuple[str, str]:
    """Returns (access_token, user_id)."""
    client.post("/auth/request-otp", json={"phone": phone})
    body = {"phone": phone, "otp": "123456"}
    if name is not None:
        body["name"] = name
    r = client.post("/auth/verify-otp", json=body)
    assert r.status_code == 200, r.text
    return r.json()["access_token"], r.json()["user"]["id"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
