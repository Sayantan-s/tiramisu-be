import pytest

from app.config import get_settings
from tests.helpers import auth, sign_in


def test_seed_roommate_creates_member_and_returns_token(client):
    token, _ = sign_in(client, "9999900001", "Alice")
    gid = client.post(
        "/groups", headers=auth(token), json={"kind": "roomies", "name": "Flat"}
    ).json()["id"]

    r = client.post(
        "/dev/seed-roommate",
        headers=auth(token),
        json={"group_id": gid, "name": "Dummy Bob"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["user"]["name"] == "Dummy Bob"
    assert body["access_token"]

    group = client.get(f"/groups/{gid}", headers=auth(token)).json()
    assert any(m["name"] == "Dummy Bob" for m in group["members"])

    me = client.get("/me", headers=auth(body["access_token"])).json()
    assert me["id"] == body["user"]["id"]


def test_seed_roommate_only_for_group_member(client):
    a_token, _ = sign_in(client, "9999900001", "Alice")
    b_token, _ = sign_in(client, "9999900002", "Bob")
    gid = client.post(
        "/groups", headers=auth(a_token), json={"kind": "roomies", "name": "Flat"}
    ).json()["id"]

    r = client.post(
        "/dev/seed-roommate",
        headers=auth(b_token),
        json={"group_id": gid, "name": "Hacker"},
    )
    assert r.status_code == 404


def test_dev_endpoint_404s_when_dev_mode_off(client, monkeypatch):
    token, _ = sign_in(client, "9999900001", "Alice")
    gid = client.post(
        "/groups", headers=auth(token), json={"kind": "roomies", "name": "Flat"}
    ).json()["id"]

    monkeypatch.setattr(get_settings(), "dev_mode", False)
    r = client.post(
        "/dev/seed-roommate", headers=auth(token), json={"group_id": gid, "name": "X"}
    )
    assert r.status_code == 404
