from datetime import datetime, timedelta, timezone

from sqlmodel import Session

from app.models import Invite
from tests.helpers import auth, sign_in


def test_create_invite_returns_code(client):
    token, _ = sign_in(client, "9999900001", "Alice")
    g = client.post(
        "/groups", headers=auth(token), json={"kind": "roomies", "name": "Flat"}
    ).json()
    r = client.post(f"/groups/{g['id']}/invites", headers=auth(token), json={})
    assert r.status_code == 201
    body = r.json()
    assert len(body["code"]) == 8
    assert body["used_count"] == 0


def test_accept_invite_adds_member(client):
    a_token, _ = sign_in(client, "9999900001", "Alice")
    b_token, b_id = sign_in(client, "9999900002", "Bob")

    g = client.post(
        "/groups", headers=auth(a_token), json={"kind": "roomies", "name": "Flat"}
    ).json()
    code = client.post(
        f"/groups/{g['id']}/invites", headers=auth(a_token), json={}
    ).json()["code"]

    r = client.post(f"/invites/{code}/accept", headers=auth(b_token))
    assert r.status_code == 200
    member_ids = [m["id"] for m in r.json()["members"]]
    assert b_id in member_ids


def test_accept_existing_member_is_idempotent(client):
    a_token, _ = sign_in(client, "9999900001", "Alice")
    g = client.post(
        "/groups", headers=auth(a_token), json={"kind": "roomies", "name": "Flat"}
    ).json()
    code = client.post(
        f"/groups/{g['id']}/invites", headers=auth(a_token), json={}
    ).json()["code"]

    r1 = client.post(f"/invites/{code}/accept", headers=auth(a_token))
    r2 = client.post(f"/invites/{code}/accept", headers=auth(a_token))
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert len(r2.json()["members"]) == 1


def test_invite_max_uses_enforced(client):
    a_token, _ = sign_in(client, "9999900001", "Alice")
    b_token, _ = sign_in(client, "9999900002", "Bob")
    c_token, _ = sign_in(client, "9999900003", "Carol")

    g = client.post(
        "/groups", headers=auth(a_token), json={"kind": "roomies", "name": "Flat"}
    ).json()
    code = client.post(
        f"/groups/{g['id']}/invites", headers=auth(a_token), json={"max_uses": 1}
    ).json()["code"]

    assert client.post(f"/invites/{code}/accept", headers=auth(b_token)).status_code == 200
    r = client.post(f"/invites/{code}/accept", headers=auth(c_token))
    assert r.status_code == 410


def test_expired_invite_rejected(client, engine):
    a_token, _ = sign_in(client, "9999900001", "Alice")
    b_token, _ = sign_in(client, "9999900002", "Bob")

    g = client.post(
        "/groups", headers=auth(a_token), json={"kind": "roomies", "name": "Flat"}
    ).json()
    code = client.post(
        f"/groups/{g['id']}/invites", headers=auth(a_token), json={}
    ).json()["code"]

    with Session(engine) as s:
        invite = s.get(Invite, code)
        invite.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        s.add(invite)
        s.commit()

    r = client.post(f"/invites/{code}/accept", headers=auth(b_token))
    assert r.status_code == 410


def test_non_member_cannot_create_invite(client):
    a_token, _ = sign_in(client, "9999900001", "Alice")
    b_token, _ = sign_in(client, "9999900002", "Bob")

    g = client.post(
        "/groups", headers=auth(a_token), json={"kind": "roomies", "name": "Flat"}
    ).json()
    r = client.post(f"/groups/{g['id']}/invites", headers=auth(b_token), json={})
    assert r.status_code == 404
