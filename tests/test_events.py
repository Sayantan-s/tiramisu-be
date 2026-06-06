from datetime import datetime, timezone

from tests.helpers import auth, sign_in


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _group(client, token) -> str:
    return client.post(
        "/groups", headers=auth(token), json={"kind": "roomies", "name": "Flat"}
    ).json()["id"]


def test_comment_event_created(client):
    token, uid = sign_in(client, "9999900001", "Alice")
    gid = _group(client, token)
    eid = client.post(
        f"/groups/{gid}/expenses",
        headers=auth(token),
        json={
            "amount": 500,
            "payer_id": uid,
            "paid_at": _now_iso(),
            "category": "food",
            "split": {"type": "equal", "participantIds": [uid]},
        },
    ).json()["id"]

    r = client.post(
        f"/groups/{gid}/events",
        headers=auth(token),
        json={"kind": "comment", "subject_id": eid, "payload": {"body": "Was this lunch?"}},
    )
    assert r.status_code == 201, r.text
    assert r.json()["kind"] == "comment"
    assert r.json()["payload"]["body"] == "Was this lunch?"


def test_comment_requires_body(client):
    token, uid = sign_in(client, "9999900001", "Alice")
    gid = _group(client, token)
    eid = client.post(
        f"/groups/{gid}/expenses",
        headers=auth(token),
        json={
            "amount": 500,
            "payer_id": uid,
            "paid_at": _now_iso(),
            "category": "food",
            "split": {"type": "equal", "participantIds": [uid]},
        },
    ).json()["id"]
    r = client.post(
        f"/groups/{gid}/events",
        headers=auth(token),
        json={"kind": "comment", "subject_id": eid, "payload": {}},
    )
    assert r.status_code == 422


def test_filter_by_month(client):
    token, uid = sign_in(client, "9999900001", "Alice")
    gid = _group(client, token)

    client.post(
        f"/groups/{gid}/expenses",
        headers=auth(token),
        json={
            "amount": 200,
            "payer_id": uid,
            "paid_at": "2026-06-15T00:00:00+00:00",
            "category": "food",
            "split": {"type": "equal", "participantIds": [uid]},
        },
    )
    client.post(
        f"/groups/{gid}/expenses",
        headers=auth(token),
        json={
            "amount": 300,
            "payer_id": uid,
            "paid_at": "2026-05-15T00:00:00+00:00",
            "category": "food",
            "split": {"type": "equal", "participantIds": [uid]},
        },
    )

    june = client.get(f"/groups/{gid}/events?month=2026-06", headers=auth(token)).json()
    assert all(e["month"] == "2026-06" for e in june)
    assert any(e["kind"] == "expense_added" for e in june)
    may = client.get(f"/groups/{gid}/events?month=2026-05", headers=auth(token)).json()
    assert all(e["month"] == "2026-05" for e in may)
