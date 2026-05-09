"""API integration tests: inference endpoints."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.inference.service import InferenceService


def _mock_service() -> MagicMock:
    svc = MagicMock(spec=InferenceService)

    health_result = MagicMock()
    health_result.model_dump.return_value = {
        "status": "healthy",
        "ollama_version": "0.1.26",
        "default_model": "gemma:latest",
        "models_available": 2,
        "latency_ms": 42.5,
    }
    svc.check_health = AsyncMock(return_value=health_result)

    model_info = MagicMock()
    model_info.model_dump.return_value = {"name": "gemma:latest", "family": "gemma", "parameter_size": "4B"}
    svc.list_models = AsyncMock(return_value=[model_info, model_info])

    svc.model_info = AsyncMock(return_value={
        "license": "MIT",
        "modelfile": "FROM gemma",
        "parameters": "temperature 0.3",
        "template": "{{ .Prompt }}",
        "details": {"family": "gemma"},
    })

    svc.generate = AsyncMock(return_value={
        "model": "gemma:latest",
        "response": "Hello, world!",
        "total_duration": 1_000_000_000,
        "load_duration": 500_000_000,
        "prompt_eval_count": 10,
        "eval_count": 20,
        "context": [1, 2, 3],
        "done": True,
    })

    svc.chat = AsyncMock(return_value={
        "model": "gemma:latest",
        "message": {"role": "assistant", "content": "Hi there!"},
        "total_duration": 800_000_000,
        "load_duration": 400_000_000,
        "prompt_eval_count": 8,
        "eval_count": 15,
        "done": True,
    })

    svc.openai_chat = AsyncMock(return_value={
        "id": "chatcmpl-123",
        "object": "chat.completion",
        "created": 1700000000,
        "model": "gemma:latest",
        "choices": [
            {"index": 0, "message": {"role": "assistant", "content": "Hello!"}, "finish_reason": "stop"}
        ],
        "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
    })

    return svc


@pytest.fixture(autouse=True)
def mock_inference():
    svc = _mock_service()
    with patch("src.api.routers.inference.get_inference_service", return_value=svc):
        yield svc


class TestInferenceAPI:
    def test_health_endpoint(self, client: TestClient, mock_inference):
        resp = client.get("/v1/inference/health")
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "healthy"
        assert "models_available" in body

    def test_list_models(self, client: TestClient, mock_inference):
        resp = client.get("/v1/inference/models")
        assert resp.status_code == 200
        body = resp.json()
        assert body["total"] == 2
        assert len(body["models"]) == 2

    def test_model_detail(self, client: TestClient, mock_inference):
        resp = client.get("/v1/inference/models/gemma:latest")
        assert resp.status_code == 200
        body = resp.json()
        assert body["name"] == "gemma:latest"
        assert "details" in body

    def test_model_detail_not_found(self, client: TestClient, mock_inference):
        mock_inference.model_info = AsyncMock(side_effect=Exception("not found"))
        resp = client.get("/v1/inference/models/nonexistent")
        assert resp.status_code == 404

    def test_generate(self, client: TestClient, mock_inference):
        resp = client.post(
            "/v1/inference/generate",
            json={"prompt": "Hello"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["response"] == "Hello, world!"
        assert body["model"] == "gemma:latest"

    def test_generate_with_system(self, client: TestClient, mock_inference):
        resp = client.post(
            "/v1/inference/generate",
            json={"prompt": "Hello", "system": "You are a helper"},
        )
        assert resp.status_code == 200

    def test_generate_with_custom_model(self, client: TestClient, mock_inference):
        resp = client.post(
            "/v1/inference/generate",
            json={"prompt": "Hello", "model": "custom-model"},
        )
        assert resp.status_code == 200

    def test_generate_empty_prompt(self, client: TestClient, mock_inference):
        resp = client.post(
            "/v1/inference/generate",
            json={"prompt": ""},
        )
        # Empty string is still valid per schema — check behavior
        assert resp.status_code in (200, 422)

    def test_generate_invalid_temperature(self, client: TestClient, mock_inference):
        resp = client.post(
            "/v1/inference/generate",
            json={"prompt": "Hello", "temperature": 5.0},
        )
        assert resp.status_code == 422

    def test_generate_llm_error(self, client: TestClient, mock_inference):
        from src.shared.exceptions import LLMError
        mock_inference.generate = AsyncMock(side_effect=LLMError("service down"))
        resp = client.post(
            "/v1/inference/generate",
            json={"prompt": "Hello"},
        )
        assert resp.status_code == 503

    def test_chat(self, client: TestClient, mock_inference):
        resp = client.post(
            "/v1/inference/chat",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "message" in body

    def test_chat_empty_messages(self, client: TestClient, mock_inference):
        resp = client.post(
            "/v1/inference/chat",
            json={"messages": []},
        )
        # Empty list may or may not be valid per schema
        assert resp.status_code in (200, 422)

    def test_openai_chat(self, client: TestClient, mock_inference):
        resp = client.post(
            "/v1/inference/v1/chat/completions",
            json={"messages": [{"role": "user", "content": "Hi"}]},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert body["object"] == "chat.completion"
        assert "choices" in body
        assert "usage" in body

    def test_openai_chat_with_params(self, client: TestClient, mock_inference):
        resp = client.post(
            "/v1/inference/v1/chat/completions",
            json={
                "messages": [{"role": "user", "content": "Hi"}],
                "model": "gemma:latest",
                "temperature": 0.5,
                "max_tokens": 100,
            },
        )
        assert resp.status_code == 200
