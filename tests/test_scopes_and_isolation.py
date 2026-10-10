"""
Integration tests for scope enforcement and tenant isolation.

These run against the real local Postgres from docker-compose, so
that container must be running. Every tenant the tests create is
named "test-..." with a random suffix, which keeps runs from
colliding with each other and makes the leftovers easy to clean up
(see the cleanup SQL in the project notes).
"""

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


# ---- helpers: each test builds its own tenants and keys ----------------


def make_tenant(label: str) -> str:
    response = client.post(
        "/tenants", json={"name": f"test-{label}-{uuid.uuid4().hex[:8]}"}
    )
    assert response.status_code == 200
    return response.json()["id"]


def make_key(tenant_id: str, scopes: list[str]) -> str:
    response = client.post("/keys", json={"tenant_id": tenant_id, "scopes": scopes})
    assert response.status_code == 200
    return response.json()["api_key"]


def auth(api_key: str) -> dict:
    return {"Authorization": f"Bearer {api_key}"}


def prefix_of(api_key: str) -> str:
    return api_key.split(".")[0]


# ---- authentication: is the key genuine? -------------------------------


def test_missing_header_is_rejected():
    # Depending on the FastAPI version, a missing header is rejected
    # as 401 or 403 by the security scheme itself. Either way it is
    # rejected before any of our code runs.
    response = client.get("/protected/ping")
    assert response.status_code in (401, 403)


def test_malformed_key_is_rejected():
    response = client.get("/protected/ping", headers=auth("not-a-real-key"))
    assert response.status_code == 401


def test_wrong_secret_is_rejected():
    key = make_key(make_tenant("a"), [])
    forged = f"{prefix_of(key)}.thisIsNotTheRealSecret"
    response = client.get("/protected/ping", headers=auth(forged))
    assert response.status_code == 401


def test_valid_key_is_accepted():
    key = make_key(make_tenant("a"), [])
    response = client.get("/protected/ping", headers=auth(key))
    assert response.status_code == 200


# ---- authorization: is the key allowed to do this? ---------------------


def test_key_without_required_scope_gets_403():
    key = make_key(make_tenant("a"), [])
    response = client.get("/keys", headers=auth(key))
    assert response.status_code == 403


def test_key_with_required_scope_can_list():
    key = make_key(make_tenant("a"), ["keys:read"])
    response = client.get("/keys", headers=auth(key))
    assert response.status_code == 200


def test_read_scope_does_not_grant_write():
    key = make_key(make_tenant("a"), ["keys:read"])
    response = client.delete(f"/keys/{uuid.uuid4()}", headers=auth(key))
    assert response.status_code == 403


# ---- tenant isolation --------------------------------------------------


def test_list_keys_only_returns_own_tenants_keys():
    key_a = make_key(make_tenant("a"), ["keys:read"])
    tenant_b = make_tenant("b")
    key_b = make_key(tenant_b, ["keys:read"])
    make_key(tenant_b, [])  # a second key for B

    a_listing = client.get("/keys", headers=auth(key_a)).json()
    b_listing = client.get("/keys", headers=auth(key_b)).json()

    assert len(a_listing) == 1
    assert len(b_listing) == 2

    a_prefixes = {k["key_prefix"] for k in a_listing}
    b_prefixes = {k["key_prefix"] for k in b_listing}
    assert a_prefixes.isdisjoint(b_prefixes)


def test_cannot_revoke_another_tenants_key():
    key_a = make_key(make_tenant("a"), ["keys:read", "keys:write"])
    key_b = make_key(make_tenant("b"), ["keys:read"])
    b_key_id = client.get("/keys", headers=auth(key_b)).json()[0]["id"]

    response = client.delete(f"/keys/{b_key_id}", headers=auth(key_a))

    # 404, not 403: A must not learn that this key exists at all.
    assert response.status_code == 404
    # And B's key must be completely unaffected.
    assert client.get("/protected/ping", headers=auth(key_b)).status_code == 200


# ---- revocation --------------------------------------------------------


def test_revoked_key_is_rejected():
    tenant = make_tenant("a")
    admin_key = make_key(tenant, ["keys:read", "keys:write"])
    victim_key = make_key(tenant, [])

    listing = client.get("/keys", headers=auth(admin_key)).json()
    victim_id = next(k["id"] for k in listing if k["key_prefix"] == prefix_of(victim_key))

    assert client.get("/protected/ping", headers=auth(victim_key)).status_code == 200
    assert client.delete(f"/keys/{victim_id}", headers=auth(admin_key)).status_code == 204
    assert client.get("/protected/ping", headers=auth(victim_key)).status_code == 401