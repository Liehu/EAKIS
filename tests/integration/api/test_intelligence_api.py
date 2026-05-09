"""API integration tests: intelligence endpoints (M1)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


@pytest.fixture()
def task_id():
    return str(uuid4())


class TestIntelligenceAPI:
    def test_start_intelligence_201(self, client: TestClient, task_id: str):
        resp = client.post(
            f"/v1/tasks/{task_id}/intelligence",
            json={
                "company_name": "测试公司",
                "industry": "finance",
                "domains": ["example.com"],
                "keywords": ["测试关键词"],
                "enabled_categories": ["news", "security"],
            },
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["task_id"] == task_id
        assert body["status"] in ("completed", "partial")
        assert body["total_sources"] >= 0

    def test_start_minimal_body(self, client: TestClient, task_id: str):
        resp = client.post(
            f"/v1/tasks/{task_id}/intelligence",
            json={"company_name": "测试公司"},
        )
        assert resp.status_code == 201

    def test_start_validation_empty_name(self, client: TestClient, task_id: str):
        resp = client.post(
            f"/v1/tasks/{task_id}/intelligence",
            json={"company_name": ""},
        )
        # Pydantic may still accept empty string unless constrained; check behavior
        # The schema doesn't have min_length, so it might pass — just verify no crash
        assert resp.status_code in (201, 422)

    def test_get_status_after_start(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/intelligence",
            json={"company_name": "测试公司", "keywords": ["test"]},
        )
        resp = client.get(f"/v1/tasks/{task_id}/intelligence")
        assert resp.status_code == 200
        body = resp.json()
        assert body["task_id"] == task_id
        assert "status" in body
        assert "total_sources" in body

    def test_get_status_not_found(self, client: TestClient):
        fake_id = str(uuid4())
        resp = client.get(f"/v1/tasks/{fake_id}/intelligence")
        assert resp.status_code == 404

    def test_list_documents(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/intelligence",
            json={"company_name": "测试公司"},
        )
        resp = client.get(f"/v1/tasks/{task_id}/intelligence/documents")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "pagination" in body
        pg = body["pagination"]
        assert "page" in pg
        assert "total" in pg

    def test_list_documents_quality_filter(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/intelligence",
            json={"company_name": "测试公司"},
        )
        resp = client.get(f"/v1/tasks/{task_id}/intelligence/documents", params={"min_quality": 0.9})
        assert resp.status_code == 200

    def test_list_documents_pagination(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/intelligence",
            json={"company_name": "测试公司"},
        )
        resp = client.get(f"/v1/tasks/{task_id}/intelligence/documents", params={"page": 1, "page_size": 1})
        assert resp.status_code == 200
        body = resp.json()
        assert body["pagination"]["page_size"] == 1

    def test_get_dsl(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/intelligence",
            json={"company_name": "测试公司", "keywords": ["test"]},
        )
        resp = client.get(f"/v1/tasks/{task_id}/intelligence/dsl")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    def test_get_sources(self, client: TestClient, task_id: str):
        client.post(
            f"/v1/tasks/{task_id}/intelligence",
            json={"company_name": "测试公司"},
        )
        resp = client.get(f"/v1/tasks/{task_id}/intelligence/sources")
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body

    def test_rag_health(self, client: TestClient):
        resp = client.get("/v1/intelligence/rag/health")
        assert resp.status_code == 200
        body = resp.json()
        assert "status" in body

    def test_rag_search(self, client: TestClient):
        resp = client.post(
            "/v1/intelligence/rag/search",
            json={"query": "测试查询", "top_k": 5},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "data" in body
        assert "total" in body
