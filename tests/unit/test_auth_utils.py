"""Unit tests for auth utilities: password hashing, JWT creation/decode."""

from __future__ import annotations

import jwt
import pytest

from src.api.auth import decode_access_token, hash_password, verify_password
from src.core.settings import get_settings


class TestPasswordUtils:
    def test_hash_password_returns_hash(self):
        h = hash_password("testpassword")
        assert h != "testpassword"
        assert len(h) > 20

    def test_verify_password_correct(self):
        h = hash_password("mysecretpass")
        assert verify_password("mysecretpass", h) is True

    def test_verify_password_incorrect(self):
        h = hash_password("mysecretpass")
        assert verify_password("wrongpass", h) is False

    def test_different_hashes_for_same_password(self):
        h1 = hash_password("samepass")
        h2 = hash_password("samepass")
        assert h1 != h2  # bcrypt uses random salt


class TestJWTUtils:
    def test_decode_valid_token(self):
        settings = get_settings()
        # Manually create a valid JWT
        payload = {"sub": "user-123", "role": "admin", "exp": 9999999999}
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        decoded = decode_access_token(token)
        assert decoded["sub"] == "user-123"
        assert decoded["role"] == "admin"

    def test_decode_expired_token_raises_401(self):
        from fastapi import HTTPException
        settings = get_settings()
        payload = {"sub": "user-123", "exp": 0}
        token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(token)
        assert exc_info.value.status_code == 401

    def test_decode_invalid_token_raises_401(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token("not.a.valid.token")
        assert exc_info.value.status_code == 401

    def test_decode_wrong_secret_raises_401(self):
        from fastapi import HTTPException
        bad_token = jwt.encode({"sub": "user-123", "exp": 9999999999}, "wrong-secret", algorithm="HS256")
        with pytest.raises(HTTPException) as exc_info:
            decode_access_token(bad_token)
        assert exc_info.value.status_code == 401
