"""API integration tests: asset discovery endpoints (M3)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def task_id():
    return str(uuid4())


class TestAssetsAPI:
    def test_start_discovery_201(self, client: TestClient, task_id: str):
        resp = client.post(
            f"/v1/tasks/{task_id}/assets/discover",
            json={
                "dsl_queries": [
                    {"platform": "fofa", "query": 'domain="example.com"'},
                    {"platform": "hunter", "query": "example.com"},
                ],
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["task_id"] == task_id
        assert body["status"] == "completed"
        assert body["total_searched"] >= 0

    def test_start_discovery_with_targets(self, client: TestClient, task_id: str):
        resp = client.post(
            f"/v1/tasks/{task_id}/assets/discover",
            json={
                "dsl_queries": [{"platform": "fofa", "query": 'domain="example.com"'}],
                "company_name": "测试公司",
                "target_domains": ["example.com"],
                "target_ip_ranges": ["1.2.3.0/24"],
            },
        )
        assert resp.status_code == 201
        assert resp.json()["avg_confidence"] >= 0

    def test_get_status_after_discovery(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/assets/discover",
            json={"dsl_queries": [{"platform": "fofa", "query": "test"}]},
        )
        resp = client.get(f"/v1/tasks/{task_id}/assets/status")
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body
        assert "total_assets" in body

    def test_get_status_not_found(self, client: TestClient):
        fake_id = str(uuid4())
        resp = client.get(f"/v1/tasks/{fake_id}/assets/status")
        assert resp.status_code == 404

    def test_list_assets(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/assets/discover",
            json={"dsl_queries": [{"platform": "fofa", "query": "test"}]},
        )
        resp = client.get(f"/v1/tasks/{task_id}/assets")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "pagination" in body

    def test_list_assets_with_type_filter(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/assets/discover",
            json={"dsl_queries": [{"platform": "fofa", "query": "test"}]},
        )
        resp = client.get(f"/v1/tasks/{task_id}/assets", params={"asset_type": "web"})
        assert resp.status_code == 200

    def test_list_assets_with_risk_filter(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/assets/discover",
            json={"dsl_queries": [{"platform": "fofa", "query": "test"}]},
        )
        resp = client.get(f"/v1/tasks/{task_id}/assets", params={"risk": "high"})
        assert resp.status_code == 200

    def test_list_assets_with_confirmed_filter(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/assets/discover",
            json={"dsl_queries": [{"platform": "fofa", "query": "test"}]},
        )
        resp = client.get(f"/v1/tasks/{task_id}/assets", params={"confirmed": "true"})
        assert resp.status_code == 200

    def test_list_assets_pagination(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/assets/discover",
            json={"dsl_queries": [{"platform": "fofa", "query": "test"}]},
        )
        resp = client.get(f"/v1/tasks/{task_id}/assets", params={"page": 1, "page_size": 5})
        assert resp.status_code == 200
        body = resp.json()
        assert body["pagination"]["page_size"] == 5

    def test_get_asset_detail(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/assets/discover",
            json={"dsl_queries": [{"platform": "fofa", "query": "test"}]},
        )
        list_resp = client.get(f"/v1/tasks/{task_id}/assets")
        assets = list_resp.json()["data"]
        if assets:
            asset_id = assets[0]["id"]
            resp = client.get(f"/v1/tasks/{task_id}/assets/{asset_id}")
            assert resp.status_code == 200
            body = resp.json()
            assert "id" in body
            assert "domain" in body
            assert "confidence" in body

    def test_get_asset_detail_not_found(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/assets/discover",
            json={"dsl_queries": [{"platform": "fofa", "query": "test"}]},
        )
        resp = client.get(f"/v1/tasks/{task_id}/assets/nonexistent-id")
        assert resp.status_code == 404

    def test_update_asset(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/assets/discover",
            json={"dsl_queries": [{"platform": "fofa", "query": "test"}]},
        )
        list_resp = client.get(f"/v1/tasks/{task_id}/assets")
        assets = list_resp.json()["data"]
        if assets:
            asset_id = assets[0]["id"]
            resp = client.patch(
                f"/v1/tasks/{task_id}/assets/{asset_id}",
                json={"confirmed": True, "risk_level": "critical", "notes": "测试更新"},
            )
            assert resp.status_code == 200
            body = resp.json()
            assert body["confirmed"] is True
            assert body["risk_level"] == "critical"

    def test_update_asset_not_found(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/assets/discover",
            json={"dsl_queries": [{"platform": "fofa", "query": "test"}]},
        )
        resp = client.patch(
            f"/v1/tasks/{task_id}/assets/nonexistent-id",
            json={"confirmed": True},
        )
        assert resp.status_code == 404

    def test_update_asset_invalid_risk(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/assets/discover",
            json={"dsl_queries": [{"platform": "fofa", "query": "test"}]},
        )
        list_resp = client.get(f"/v1/tasks/{task_id}/assets")
        assets = list_resp.json()["data"]
        if assets:
            asset_id = assets[0]["id"]
            resp = client.patch(
                f"/v1/tasks/{task_id}/assets/{asset_id}",
                json={"risk_level": "invalid"},
            )
            assert resp.status_code == 422
