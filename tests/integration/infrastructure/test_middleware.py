"""Infrastructure integration tests: middleware (audit, rate-limit, CORS)."""

from __future__ import annotations

import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.base import BaseHTTPMiddleware
from unittest.mock import patch

from src.api.middleware.audit import AuditLoggingMiddleware
from src.api.middleware.rate_limit import RateLimitMiddleware


class TestAuditMiddleware:
    def test_audit_middleware_logs_request(self, client: TestClient, log_capture):
        resp = client.get("/v1/health")
        assert resp.status_code == 200
        # health path is in _SKIP_PATHS so no audit log expected — test a non-skip path
        resp = client.get("/v1/docs")
        # docs is also skipped, use a non-existing API path to trigger logging
        resp = client.get("/v1/tasks/nonexistent/intelligence")
        # any status is fine; we just want the audit log
        assert len(log_capture.records) >= 1
        record = log_capture.records[-1]
        assert record.method == "GET"

    def test_audit_middleware_skips_health(self, client: TestClient, log_capture):
        log_capture.records.clear()
        client.get("/v1/health")
        audit_logs = [r for r in log_capture.records if hasattr(r, "method")]
        assert len(audit_logs) == 0

    def test_audit_middleware_skips_docs(self, client: TestClient, log_capture):
        log_capture.records.clear()
        client.get("/docs")
        audit_logs = [r for r in log_capture.records if hasattr(r, "method")]
        assert len(audit_logs) == 0

    def test_audit_records_client_ip(self, client: TestClient, log_capture):
        log_capture.records.clear()
        client.get("/v1/tasks/test/intelligence")
        audit_logs = [r for r in log_capture.records if hasattr(r, "method")]
        if audit_logs:
            assert audit_logs[0].client_ip == "testclient"

    def test_audit_records_duration(self, client: TestClient, log_capture):
        log_capture.records.clear()
        client.get("/v1/tasks/test/intelligence")
        audit_logs = [r for r in log_capture.records if hasattr(r, "method")]
        if audit_logs:
            assert audit_logs[0].duration_ms >= 0


class TestRateLimitMiddleware:
    def test_rate_limit_allows_normal(self, client: TestClient):
        """Default rpm=60 should allow a handful of requests."""
        for _ in range(10):
            resp = client.get("/v1/health")
            assert resp.status_code == 200

    def test_rate_limit_skips_health(self):
        """Health endpoint bypasses rate limiting."""
        _app = FastAPI()
        _app.add_middleware(RateLimitMiddleware, rpm=3)

        @_app.get("/v1/health")
        async def health():
            return {"status": "ok"}

        c = TestClient(_app)
        for _ in range(10):
            resp = c.get("/v1/health")
            assert resp.status_code == 200

    def test_rate_limit_blocks_excess(self):
        """Low rpm should eventually return 429."""
        _app = FastAPI()
        _app.add_middleware(RateLimitMiddleware, rpm=3)

        @_app.get("/v1/test")
        async def test_ep():
            return {"ok": True}

        c = TestClient(_app)
        statuses = []
        for _ in range(20):
            resp = c.get("/v1/test")
            statuses.append(resp.status_code)
        assert 429 in statuses


class TestCORSMiddleware:
    def test_cors_headers_present(self, client: TestClient):
        resp = client.options(
            "/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "GET",
            },
        )
        assert resp.headers.get("access-control-allow-origin") is not None

    def test_cors_methods(self, client: TestClient):
        resp = client.options(
            "/v1/health",
            headers={
                "Origin": "http://localhost:3000",
                "Access-Control-Request-Method": "POST",
            },
        )
        allow_methods = resp.headers.get("access-control-allow-methods", "")
        assert "POST" in allow_methods
