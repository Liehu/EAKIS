"""Infrastructure integration tests: settings, configuration, and exception hierarchy."""

from __future__ import annotations

import pytest

from src.core.settings import Settings, get_settings
from src.models.database import Base
from src.shared.exceptions import (
    EAKISBaseError,
    LLMError,
    CircuitOpenError,
    AuthenticationError,
    RateLimitExceededError,
    TaskNotFoundError,
    PipelineError,
)


class TestSettings:
    def test_defaults(self):
        s = Settings(
            _env_file=None,
            openai_api_key="test",
        )
        assert s.debug is True
        assert s.intelligence_use_stubs is True
        assert s.crawler_use_stubs is True
        assert s.asset_discovery_use_stubs is True
        assert s.rag_use_stubs is True
        assert s.jwt_algorithm == "HS256"
        assert s.rate_limit_rpm == 60

    def test_singleton(self):
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_from_env(self, monkeypatch):
        monkeypatch.setenv("INTELLIGENCE_USE_STUBS", "false")
        s = Settings(_env_file=None)
        # This reads from env vars; the default is True but we set it to false
        # Note: pydantic-settings reads from env automatically
        assert s.intelligence_use_stubs is False
        monkeypatch.undo()


class TestDatabaseBase:
    def test_base_has_metadata(self):
        assert hasattr(Base, "metadata")
        assert Base.metadata is not None

    def test_tables_registered(self):
        """Verify that model tables have been registered on Base.metadata."""
        table_names = Base.metadata.tables.keys()
        assert len(table_names) > 0


class TestExceptionHierarchy:
    def test_llm_error(self):
        err = LLMError("test")
        assert err.code == "LLM_ERROR"
        assert err.http_status == 500
        assert isinstance(err, EAKISBaseError)

    def test_circuit_open_error(self):
        err = CircuitOpenError("circuit open")
        assert err.code == "CIRCUIT_OPEN"
        assert err.http_status == 503
        assert isinstance(err, EAKISBaseError)

    def test_auth_error(self):
        err = AuthenticationError("bad token")
        assert err.code == "AUTHENTICATION_ERROR"
        assert err.http_status == 401

    def test_rate_limit_error(self):
        err = RateLimitExceededError("too many")
        assert err.code == "RATE_LIMIT_EXCEEDED"
        assert err.http_status == 429

    def test_task_not_found(self):
        err = TaskNotFoundError("no task")
        assert err.code == "TASK_NOT_FOUND"
        assert err.http_status == 404

    def test_pipeline_error(self):
        err = PipelineError("pipeline broke")
        assert err.code == "PIPELINE_ERROR"
        assert err.http_status == 500

    def test_custom_code_and_status(self):
        err = EAKISBaseError("msg", code="CUSTOM", http_status=418)
        assert err.code == "CUSTOM"
        assert err.http_status == 418
