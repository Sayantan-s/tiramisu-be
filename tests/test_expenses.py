from datetime import datetime, timezone

from tests.helpers import auth, sign_in


def _group(client, token, name="Flat 4B") -> str:
    return client.post(
        "/groups", headers=auth(token), json={"kind": "roomies", "name": name}
    ).json()["id"]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def test_create_expense_returns_payload_and_emits_event(client):
    token, uid = sign_in(client, "9999900001", "Alice")
    gid = _group(client, token)

    r = client.post(
        f"/groups/{gid}/expenses",
        headers=auth(token),
        json={
            "amount": 1000,
            "payer_id": uid,
            "paid_at": _now_iso(),
            "category": "groceries",
            "description": "Vegetables",
            "split": {"type": "equal", "participantIds": [uid]},
        },
    )
    assert r.status_code == 201, r.text
    expense = r.json()
    assert expense["amount"] == 1000
    assert expense["created_by"] == uid

    events = client.get(f"/groups/{gid}/events", headers=auth(token)).json()
    assert any(
        e["kind"] == "expense_added" and e["subject_id"] == expense["id"] for e in events
    )


def test_invalid_split_rejected(client):
    token, uid = sign_in(client, "9999900001", "Alice")
    gid = _group(client, token)
    r = client.post(
        f"/groups/{gid}/expenses",
        headers=auth(token),
        json={
            "amount": 1000,
            "payer_id": uid,
            "paid_at": _now_iso(),
            "category": "groceries",
            "split": {"type": "exact", "amounts": {uid: 200}},
        },
    )
    assert r.status_code == 422


def test_list_excludes_soft_deleted(client):
    token, uid = sign_in(client, "9999900001", "Alice")
    gid = _group(client, token)
    eid = client.post(
        f"/groups/{gid}/expenses",
        headers=auth(token),
        json={
            "amount": 500,
            "payer_id": uid,
            "paid_at": _now_iso(),
            "category": "groceries",
            "split": {"type": "equal", "participantIds": [uid]},
        },
    ).json()["id"]

    assert client.delete(f"/groups/{gid}/expenses/{eid}", headers=auth(token)).status_code == 204
    rows = client.get(f"/groups/{gid}/expenses", headers=auth(token)).json()
    assert all(e["id"] != eid for e in rows)


def test_non_member_cannot_list(client):
    a_token, a_id = sign_in(client, "9999900001", "Alice")
    b_token, _ = sign_in(client, "9999900002", "Bob")
    gid = _group(client, a_token)
    r = client.get(f"/groups/{gid}/expenses", headers=auth(b_token))
    assert r.status_code == 404
