from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.api.main import app

_T1 = "00000000-0000-0000-0000-000000000001"
_T2 = "00000000-0000-0000-0000-000000000002"
_T3 = "00000000-0000-0000-0000-000000000003"
_T4 = "00000000-0000-0000-0000-000000000004"
_T5 = "00000000-0000-0000-0000-000000000005"
_T6 = "00000000-0000-0000-0000-000000000006"
_T7 = "00000000-0000-0000-0000-000000000007"


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_start_crawl(client: AsyncClient):
    resp = await client.post(
        f"/v1/tasks/{_T1}/interfaces/crawl",
        json={"assets": [{"asset_id": "a1", "url": "https://example.com"}]},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] in ("completed", "failed")
    assert "total_classified" in data


@pytest.mark.asyncio
async def test_list_interfaces_before_crawl(client: AsyncClient):
    resp = await client.get(f"/v1/tasks/{_T2}/interfaces")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_list_interfaces_after_crawl(client: AsyncClient):
    await client.post(
        f"/v1/tasks/{_T3}/interfaces/crawl",
        json={"assets": [{"asset_id": "a1", "url": "https://example.com"}]},
    )
    resp = await client.get(f"/v1/tasks/{_T3}/interfaces")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_get_interface_detail(client: AsyncClient):
    await client.post(
        f"/v1/tasks/{_T4}/interfaces/crawl",
        json={"assets": [{"asset_id": "a1", "url": "https://example.com"}]},
    )
    list_resp = await client.get(f"/v1/tasks/{_T4}/interfaces")
    interfaces = list_resp.json()["data"]
    if interfaces:
        iface_id = interfaces[0]["interface_id"]
        detail_resp = await client.get(
            f"/v1/tasks/{_T4}/interfaces/{iface_id}"
        )
        assert detail_resp.status_code == 200
        assert detail_resp.json()["interface_id"] == iface_id


@pytest.mark.asyncio
async def test_update_interface(client: AsyncClient):
    await client.post(
        f"/v1/tasks/{_T5}/interfaces/crawl",
        json={"assets": [{"asset_id": "a1", "url": "https://example.com"}]},
    )
    list_resp = await client.get(f"/v1/tasks/{_T5}/interfaces")
    interfaces = list_resp.json()["data"]
    if interfaces:
        iface_id = interfaces[0]["interface_id"]
        update_resp = await client.patch(
            f"/v1/tasks/{_T5}/interfaces/{iface_id}",
            json={"test_priority": 10, "notes": "high risk"},
        )
        assert update_resp.status_code == 200
        assert update_resp.json()["test_priority"] == 10


@pytest.mark.asyncio
async def test_get_crawl_status(client: AsyncClient):
    await client.post(
        f"/v1/tasks/{_T6}/interfaces/crawl",
        json={"assets": [{"asset_id": "a1", "url": "https://example.com"}]},
    )
    resp = await client.get(f"/v1/tasks/{_T6}/interfaces/status")
    assert resp.status_code == 200
    assert "status" in resp.json()


@pytest.mark.asyncio
async def test_get_nonexistent_interface(client: AsyncClient):
    await client.post(
        f"/v1/tasks/{_T7}/interfaces/crawl",
        json={"assets": [{"asset_id": "a1", "url": "https://example.com"}]},
    )
    resp = await client.get(
        f"/v1/tasks/{_T7}/interfaces/00000000-0000-0000-0000-999999999999"
    )
    assert resp.status_code == 404
