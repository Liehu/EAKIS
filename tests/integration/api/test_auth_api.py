"""API integration tests: authentication endpoints."""

from __future__ import annotations

from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from src.api.auth import create_access_token, decode_access_token
from src.core.settings import get_settings


class TestAuthAPI:
    def test_login_admin_success(self, client: TestClient):
        resp = client.post(
            "/v1/auth/token",
            data={"username": "admin", "password": "eakis2024"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"

    def test_login_analyst_success(self, client: TestClient):
        resp = client.post(
            "/v1/auth/token",
            data={"username": "analyst", "password": "eakis2024"},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_login_wrong_password(self, client: TestClient):
        resp = client.post(
            "/v1/auth/token",
            data={"username": "admin", "password": "wrong"},
        )
        assert resp.status_code == 401
        assert "www-authenticate" in resp.headers

    def test_login_nonexistent_user(self, client: TestClient):
        resp = client.post(
            "/v1/auth/token",
            data={"username": "nobody", "password": "eakis2024"},
        )
        assert resp.status_code == 401

    def test_token_is_valid_jwt(self):
        token = create_access_token(data={"sub": "admin", "role": "admin"})
        settings = get_settings()
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        assert payload["sub"] == "admin"
        assert payload["role"] == "admin"

    def test_token_expired(self):
        token = create_access_token(data={"sub": "admin"}, expires_delta=timedelta(seconds=-1))
        from fastapi import HTTPException
        try:
            decode_access_token(token)
            assert False, "Should have raised"
        except HTTPException as e:
            assert e.status_code == 401

    def test_token_invalid_signature(self):
        from fastapi import HTTPException
        bad_token = jwt.encode({"sub": "admin"}, "wrong-secret", algorithm="HS256")
        try:
            decode_access_token(bad_token)
            assert False, "Should have raised"
        except HTTPException as e:
            assert e.status_code == 401
