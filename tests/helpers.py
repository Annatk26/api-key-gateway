"""Small helpers shared by the test files."""

import uuid

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


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