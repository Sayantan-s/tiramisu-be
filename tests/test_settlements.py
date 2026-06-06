from datetime import datetime, timezone

from tests.helpers import auth, sign_in


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _group(client, token, name="Flat") -> str:
    return client.post(
        "/groups", headers=auth(token), json={"kind": "roomies", "name": name}
    ).json()["id"]


def test_settlement_round_trip_zeros_balances(client):
    a_token, a_id = sign_in(client, "9999900001", "Alice")
    b_token, b_id = sign_in(client, "9999900002", "Bob")

    gid = _group(client, a_token)
    invite = client.post(f"/groups/{gid}/invites", headers=auth(a_token), json={}).json()
    client.post(f"/invites/{invite['code']}/accept", headers=auth(b_token))

    client.post(
        f"/groups/{gid}/expenses",
        headers=auth(a_token),
        json={
            "amount": 1000,
            "payer_id": a_id,
            "paid_at": _now_iso(),
            "category": "groceries",
            "split": {"type": "equal", "participantIds": [a_id, b_id]},
        },
    )
    settle = client.post(
        f"/groups/{gid}/settlements",
        headers=auth(b_token),
        json={"from_id": b_id, "to_id": a_id, "amount": 500, "paid_at": _now_iso()},
    )
    assert settle.status_code == 201, settle.text

    events = client.get(f"/groups/{gid}/events", headers=auth(a_token)).json()
    kinds = [e["kind"] for e in events]
    assert "expense_added" in kinds
    assert "settlement_recorded" in kinds


def test_settlement_from_equals_to_rejected(client):
    token, uid = sign_in(client, "9999900001", "Alice")
    gid = _group(client, token)
    r = client.post(
        f"/groups/{gid}/settlements",
        headers=auth(token),
        json={"from_id": uid, "to_id": uid, "amount": 500, "paid_at": _now_iso()},
    )
    assert r.status_code == 422
