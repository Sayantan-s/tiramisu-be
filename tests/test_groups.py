from tests.helpers import auth, sign_in


def test_create_group_makes_creator_owner(client):
    token, uid = sign_in(client, "9999900001", name="Alice")
    r = client.post(
        "/groups",
        headers=auth(token),
        json={"kind": "roomies", "name": "Flat 4B", "icon": "🏠"},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["kind"] == "roomies"
    assert body["name"] == "Flat 4B"
    assert len(body["members"]) == 1
    assert body["members"][0]["id"] == uid
    assert body["members"][0]["role"] == "owner"


def test_list_groups_only_returns_mine(client):
    a_token, _ = sign_in(client, "9999900001", "Alice")
    b_token, _ = sign_in(client, "9999900002", "Bob")

    client.post(
        "/groups", headers=auth(a_token), json={"kind": "roomies", "name": "Alice's flat"}
    )
    client.post(
        "/groups", headers=auth(b_token), json={"kind": "roomies", "name": "Bob's flat"}
    )

    a_groups = client.get("/groups", headers=auth(a_token)).json()
    b_groups = client.get("/groups", headers=auth(b_token)).json()
    assert [g["name"] for g in a_groups] == ["Alice's flat"]
    assert [g["name"] for g in b_groups] == ["Bob's flat"]


def test_read_group_rejects_non_member(client):
    a_token, _ = sign_in(client, "9999900001", "Alice")
    b_token, _ = sign_in(client, "9999900002", "Bob")

    gid = client.post(
        "/groups", headers=auth(a_token), json={"kind": "roomies", "name": "Flat 4B"}
    ).json()["id"]

    r = client.get(f"/groups/{gid}", headers=auth(b_token))
    assert r.status_code == 404


def test_owner_can_delete_group(client):
    token, _ = sign_in(client, "9999900001", "Alice")
    gid = client.post(
        "/groups", headers=auth(token), json={"kind": "roomies", "name": "Flat 4B"}
    ).json()["id"]
    r = client.delete(f"/groups/{gid}", headers=auth(token))
    assert r.status_code == 204
    assert client.get(f"/groups/{gid}", headers=auth(token)).status_code == 404


def test_non_owner_cannot_delete_group(client):
    a_token, _ = sign_in(client, "9999900001", "Alice")
    b_token, _ = sign_in(client, "9999900002", "Bob")

    g = client.post(
        "/groups", headers=auth(a_token), json={"kind": "roomies", "name": "Flat 4B"}
    ).json()
    invite = client.post(
        f"/groups/{g['id']}/invites", headers=auth(a_token), json={}
    ).json()
    client.post(f"/invites/{invite['code']}/accept", headers=auth(b_token))

    r = client.delete(f"/groups/{g['id']}", headers=auth(b_token))
    assert r.status_code == 403


def test_leave_promotes_oldest_when_owner_leaves(client):
    a_token, a_id = sign_in(client, "9999900001", "Alice")
    b_token, b_id = sign_in(client, "9999900002", "Bob")

    g = client.post(
        "/groups", headers=auth(a_token), json={"kind": "roomies", "name": "Flat 4B"}
    ).json()
    invite = client.post(
        f"/groups/{g['id']}/invites", headers=auth(a_token), json={}
    ).json()
    client.post(f"/invites/{invite['code']}/accept", headers=auth(b_token))

    r = client.post(f"/groups/{g['id']}/leave", headers=auth(a_token))
    assert r.status_code == 204

    body = client.get(f"/groups/{g['id']}", headers=auth(b_token)).json()
    assert [m["id"] for m in body["members"]] == [b_id]
    assert body["members"][0]["role"] == "owner"


def test_leave_last_member_deletes_group(client):
    token, _ = sign_in(client, "9999900001", "Alice")
    g = client.post(
        "/groups", headers=auth(token), json={"kind": "roomies", "name": "Solo"}
    ).json()
    r = client.post(f"/groups/{g['id']}/leave", headers=auth(token))
    assert r.status_code == 204
    assert client.get(f"/groups/{g['id']}", headers=auth(token)).status_code == 404
