"""API integration tests: interface crawler endpoints (M4)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def task_id():
    return str(uuid4())


def _start_crawl(client: TestClient, task_id: str, n_assets: int = 1):
    assets = [
        {"asset_id": f"asset-{i}", "url": f"https://example{i}.com"}
        for i in range(n_assets)
    ]
    return client.post(
        f"/v1/tasks/{task_id}/interfaces/crawl",
        json={"assets": assets},
    )


class TestInterfacesAPI:
    def test_start_crawl_201(self, client: TestClient, task_id: str):
        resp = _start_crawl(client, task_id)
        if resp.status_code == 429:
            pytest.skip("Rate limited by prior tests")
        assert resp.status_code == 201
        body = resp.json()
        assert body["task_id"] == task_id
        assert body["status"] == "completed"
        assert body["total_assets"] >= 1

    def test_start_crawl_multiple_assets(self, client: TestClient, task_id: str):
        resp = _start_crawl(client, task_id, n_assets=3)
        assert resp.status_code == 201
        body = resp.json()
        assert body["total_assets"] == 3

    def test_get_crawl_status(self, client: TestClient, task_id: str):
        _start_crawl(client, task_id)
        resp = client.get(f"/v1/tasks/{task_id}/interfaces/status")
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body
        assert "total_interfaces" in body

    def test_get_crawl_status_not_found(self, client: TestClient):
        resp = client.get(f"/v1/tasks/{uuid4()}/interfaces/status")
        assert resp.status_code == 404

    def test_list_interfaces(self, client: TestClient, task_id: str):
        _start_crawl(client, task_id)
        resp = client.get(f"/v1/tasks/{task_id}/interfaces")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "summary" in body
        summary = body["summary"]
        assert "total" in summary
        assert "by_type" in summary

    def test_list_interfaces_filter_asset_id(self, client: TestClient, task_id: str):
        _start_crawl(client, task_id)
        resp = client.get(f"/v1/tasks/{task_id}/interfaces", params={"asset_id": "asset-0"})
        assert resp.status_code == 200

    def test_list_interfaces_filter_method(self, client: TestClient, task_id: str):
        _start_crawl(client, task_id)
        resp = client.get(f"/v1/tasks/{task_id}/interfaces", params={"method": "GET"})
        assert resp.status_code == 200

    def test_list_interfaces_filter_privilege(self, client: TestClient, task_id: str):
        _start_crawl(client, task_id)
        resp = client.get(f"/v1/tasks/{task_id}/interfaces", params={"privilege_sensitive": "true"})
        assert resp.status_code == 200

    def test_list_interfaces_pagination(self, client: TestClient, task_id: str):
        _start_crawl(client, task_id)
        resp = client.get(f"/v1/tasks/{task_id}/interfaces", params={"page": 1, "page_size": 5})
        assert resp.status_code == 200
        body = resp.json()
        assert body["pagination"]["page_size"] == 5

    def test_get_interface_detail(self, client: TestClient, task_id: str):
        _start_crawl(client, task_id)
        list_resp = client.get(f"/v1/tasks/{task_id}/interfaces")
        ifaces = list_resp.json()["data"]
        if ifaces:
            iface_id = ifaces[0]["interface_id"]
            resp = client.get(f"/v1/tasks/{task_id}/interfaces/{iface_id}")
            assert resp.status_code == 200
            body = resp.json()
            assert "interface_id" in body
            assert "asset_id" in body
            assert "path" in body
            assert "method" in body

    def test_get_interface_detail_not_found(self, client: TestClient, task_id: str):
        _start_crawl(client, task_id)
        resp = client.get(f"/v1/tasks/{task_id}/interfaces/nonexistent-id")
        assert resp.status_code == 404

    def test_update_interface(self, client: TestClient, task_id: str):
        _start_crawl(client, task_id)
        list_resp = client.get(f"/v1/tasks/{task_id}/interfaces")
        ifaces = list_resp.json()["data"]
        if ifaces:
            iface_id = ifaces[0]["interface_id"]
            resp = client.patch(
                f"/v1/tasks/{task_id}/interfaces/{iface_id}",
                json={"test_priority": 10, "notes": "高风险接口", "skip_test": True},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["test_priority"] == 10
            assert body["skip_test"] is True

    def test_update_interface_not_found(self, client: TestClient, task_id: str):
        _start_crawl(client, task_id)
        resp = client.patch(
            f"/v1/tasks/{task_id}/interfaces/nonexistent-id",
            json={"test_priority": 5},
        )
        assert resp.status_code == 404
