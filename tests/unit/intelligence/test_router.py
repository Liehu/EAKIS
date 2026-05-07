import pytest
from fastapi.testclient import TestClient

from src.api.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_start_intelligence(client):
    resp = client.post(
        "/v1/tasks/00000000-0000-0000-0000-000000000001/intelligence",
        json={
            "company_name": "XX支付科技有限公司",
            "industry": "fintech",
            "keywords": ["XX支付", "Spring Boot"],
            "domains": ["xx-payment.com"],
        },
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["status"] in ("completed", "partial_failure")
    assert data["total_sources"] > 0


def test_get_intelligence_status(client):
    task_id = "00000000-0000-0000-0000-000000000002"
    client.post(
        f"/v1/tasks/{task_id}/intelligence",
        json={"company_name": "XX科技"},
    )
    resp = client.get(f"/v1/tasks/{task_id}/intelligence")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] in ("completed", "partial_failure")
    assert "sources" in data


def test_get_intelligence_status_not_found(client):
    resp = client.get("/v1/tasks/00000000-0000-0000-0000-999999999999/intelligence")
    assert resp.status_code == 404


def test_list_documents(client):
    task_id = "00000000-0000-0000-0000-000000000003"
    client.post(
        f"/v1/tasks/{task_id}/intelligence",
        json={"company_name": "XX科技", "keywords": ["XX科技"]},
    )
    resp = client.get(f"/v1/tasks/{task_id}/intelligence/documents")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data
    assert "pagination" in data


def test_list_documents_with_quality_filter(client):
    task_id = "00000000-0000-0000-0000-000000000004"
    client.post(
        f"/v1/tasks/{task_id}/intelligence",
        json={"company_name": "XX科技"},
    )
    resp = client.get(f"/v1/tasks/{task_id}/intelligence/documents?min_quality=0.8")
    assert resp.status_code == 200


def test_get_dsl(client):
    task_id = "00000000-0000-0000-0000-000000000005"
    client.post(
        f"/v1/tasks/{task_id}/intelligence",
        json={"company_name": "XX科技", "keywords": ["XX科技"], "domains": ["xx-tech.com"]},
    )
    resp = client.get(f"/v1/tasks/{task_id}/intelligence/dsl")
    assert resp.status_code == 200
    data = resp.json()
    assert "data" in data


def test_get_sources(client):
    task_id = "00000000-0000-0000-0000-000000000006"
    client.post(
        f"/v1/tasks/{task_id}/intelligence",
        json={"company_name": "XX科技"},
    )
    resp = client.get(f"/v1/tasks/{task_id}/intelligence/sources")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["data"]) > 0
