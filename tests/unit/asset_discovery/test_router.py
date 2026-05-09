"""Unit tests for asset API router."""
from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from src.api.main import app

UUID_100 = str(uuid.uuid4())
UUID_200 = str(uuid.uuid4())
UUID_300 = str(uuid.uuid4())
UUID_301 = str(uuid.uuid4())
UUID_400 = str(uuid.uuid4())
UUID_500 = str(uuid.uuid4())


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.anyio
class TestAssetRouter:
    async def test_start_discovery(self, client):
        resp = await client.post(
            f"/v1/tasks/{UUID_100}/assets/discover",
            json={
                "dsl_queries": [
                    {"platform": "fofa", "query": 'domain="example.com"'},
                ],
                "target_domains": ["example.com"],
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["task_id"] == UUID_100
        assert data["status"] in ("completed", "partial_failure")
        assert data["total_searched"] > 0

    async def test_get_discovery_status(self, client):
        await client.post(
            f"/v1/tasks/{UUID_200}/assets/discover",
            json={"dsl_queries": [{"platform": "fofa", "query": "test"}]},
        )
        resp = await client.get(f"/v1/tasks/{UUID_200}/assets/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "completed"
        assert data["total_assets"] >= 0

    async def test_get_discovery_status_not_found(self, client):
        resp = await client.get(f"/v1/tasks/{uuid.uuid4()}/assets/status")
        assert resp.status_code == 404

    async def test_list_assets(self, client):
        await client.post(
            f"/v1/tasks/{UUID_300}/assets/discover",
            json={"dsl_queries": [{"platform": "fofa", "query": "test"}]},
        )
        resp = await client.get(f"/v1/tasks/{UUID_300}/assets")
        assert resp.status_code == 200
        data = resp.json()
        assert "data" in data
        assert "pagination" in data

    async def test_list_assets_with_filters(self, client):
        await client.post(
            f"/v1/tasks/{UUID_301}/assets/discover",
            json={"dsl_queries": [{"platform": "fofa", "query": "test"}]},
        )
        resp = await client.get(
            f"/v1/tasks/{UUID_301}/assets",
            params={"asset_type": "api", "page": 1, "page_size": 5},
        )
        assert resp.status_code == 200

    async def test_list_assets_not_found(self, client):
        resp = await client.get(f"/v1/tasks/{uuid.uuid4()}/assets")
        assert resp.status_code == 404

    async def test_get_asset_detail(self, client):
        await client.post(
            f"/v1/tasks/{UUID_400}/assets/discover",
            json={"dsl_queries": [{"platform": "fofa", "query": "test"}]},
        )
        list_resp = await client.get(f"/v1/tasks/{UUID_400}/assets")
        assets = list_resp.json()["data"]
        if assets:
            asset_id = assets[0]["id"]
            resp = await client.get(
                f"/v1/tasks/{UUID_400}/assets/{asset_id}"
            )
            assert resp.status_code == 200
            assert resp.json()["id"] == asset_id

    async def test_get_asset_detail_not_found(self, client):
        resp = await client.get(f"/v1/tasks/{UUID_400}/assets/nonexistent-id")
        assert resp.status_code == 404

    async def test_update_asset(self, client):
        await client.post(
            f"/v1/tasks/{UUID_500}/assets/discover",
            json={"dsl_queries": [{"platform": "fofa", "query": "test"}]},
        )
        list_resp = await client.get(f"/v1/tasks/{UUID_500}/assets")
        assets = list_resp.json()["data"]
        if assets:
            asset_id = assets[0]["id"]
            resp = await client.patch(
                f"/v1/tasks/{UUID_500}/assets/{asset_id}",
                json={"confirmed": True, "risk_level": "high", "notes": "Critical asset"},
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["confirmed"] is True
            assert data["risk_level"] == "high"
            assert data["notes"] == "Critical asset"

    async def test_update_asset_not_found(self, client):
        resp = await client.patch(
            f"/v1/tasks/{UUID_500}/assets/nonexistent-id",
            json={"confirmed": True},
        )
        assert resp.status_code == 404

    async def test_update_asset_invalid_risk(self, client):
        resp = await client.patch(
            f"/v1/tasks/{UUID_500}/assets/some-id",
            json={"risk_level": "invalid"},
        )
        assert resp.status_code == 422
