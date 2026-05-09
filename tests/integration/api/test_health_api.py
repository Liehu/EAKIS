"""API integration tests: health + docs endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


class TestHealthAPI:
    def test_health_returns_ok(self, client: TestClient):
        resp = client.get("/v1/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "ok"
        assert "version" in body

    def test_health_no_auth_required(self, client: TestClient):
        """Health endpoint works without any auth header."""
        resp = client.get("/v1/health")
        assert resp.status_code == 200

    def test_docs_accessible(self, client: TestClient):
        resp = client.get("/docs")
        assert resp.status_code == 200

    def test_openapi_json_accessible(self, client: TestClient):
        resp = client.get("/v1/openapi.json")
        assert resp.status_code == 200
        schema = resp.json()
        assert "paths" in schema
        assert "/v1/health" in schema["paths"]
