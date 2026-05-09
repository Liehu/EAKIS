"""Unit tests for inference API router."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from src.inference.service import InferenceService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_service():
    svc = MagicMock(spec=InferenceService)

    svc.check_health = AsyncMock(return_value=MagicMock(
        model_dump=lambda: {
            "status": "healthy",
            "ollama_version": "0.5.0",
            "default_model": "test-model:latest",
            "models_available": 2,
            "latency_ms": 15.3,
        }
    ))

    from src.inference.service import ModelInfo
    svc.list_models = AsyncMock(return_value=[
        ModelInfo(name="gemma:latest", size=4700000000, family="gemma",
                  parameter_size="4B", quantization="Q4_K_M", format="gguf"),
        ModelInfo(name="qwen:latest", size=4400000000, family="qwen2",
                  parameter_size="7B", quantization="Q4_K_M", format="gguf"),
    ])

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
        "total_duration": 1000000000,
        "load_duration": 500000000,
        "prompt_eval_count": 10,
        "eval_count": 5,
        "context": [1, 2, 3],
        "done": True,
    })

    svc.chat = AsyncMock(return_value={
        "model": "gemma:latest",
        "message": {"role": "assistant", "content": "Hi there!"},
        "total_duration": 800000000,
        "load_duration": 400000000,
        "prompt_eval_count": 8,
        "eval_count": 4,
        "done": True,
    })

    svc.openai_chat = AsyncMock(return_value={
        "id": "chatcmpl-abc",
        "object": "chat.completion",
        "created": 1234567890,
        "model": "gemma:latest",
        "choices": [{"index": 0, "message": {"role": "assistant", "content": "Hello"}, "finish_reason": "stop"}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 2, "total_tokens": 7},
    })

    return svc


@pytest.fixture
def client(mock_service):
    with patch("src.api.routers.inference.get_inference_service", return_value=mock_service):
        from contextlib import asynccontextmanager

        @asynccontextmanager
        async def noop_lifespan(app):
            yield

        from src.api.main import app
        app.router.lifespan_context = noop_lifespan
        with TestClient(app) as c:
            yield c


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

def test_health_endpoint(client):
    r = client.get("/v1/inference/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "healthy"
    assert data["models_available"] == 2
    assert "latency_ms" in data


# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

def test_list_models(client):
    r = client.get("/v1/inference/models")
    assert r.status_code == 200
    data = r.json()
    assert data["total"] == 2
    assert data["models"][0]["name"] == "gemma:latest"
    assert data["models"][1]["name"] == "qwen:latest"


def test_model_detail(client):
    r = client.get("/v1/inference/models/gemma:latest")
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "gemma:latest"
    assert data["license"] == "MIT"


def test_model_detail_not_found(client, mock_service):
    mock_service.model_info = AsyncMock(side_effect=Exception("not found"))
    r = client.get("/v1/inference/models/nonexistent")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------

def test_generate_endpoint(client):
    r = client.post("/v1/inference/generate", json={
        "prompt": "Say hello",
        "temperature": 0.3,
    })
    assert r.status_code == 200
    data = r.json()
    assert data["response"] == "Hello, world!"
    assert data["model"] == "gemma:latest"
    assert data["eval_count"] == 5


def test_generate_with_system(client):
    r = client.post("/v1/inference/generate", json={
        "prompt": "Test",
        "system": "You are a security expert",
    })
    assert r.status_code == 200


def test_generate_with_custom_model(client):
    r = client.post("/v1/inference/generate", json={
        "prompt": "Test",
        "model": "custom-model",
    })
    assert r.status_code == 200


def test_generate_validation_empty_prompt(client):
    r = client.post("/v1/inference/generate", json={
        "prompt": "",
    })
    assert r.status_code == 422  # Validation error


def test_generate_validation_invalid_temperature(client):
    r = client.post("/v1/inference/generate", json={
        "prompt": "Test",
        "temperature": 5.0,
    })
    assert r.status_code == 422


def test_generate_llm_error(client, mock_service):
    from src.shared.exceptions import LLMError
    mock_service.generate = AsyncMock(side_effect=LLMError("Service unavailable"))
    r = client.post("/v1/inference/generate", json={"prompt": "Test"})
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

def test_chat_endpoint(client):
    r = client.post("/v1/inference/chat", json={
        "messages": [{"role": "user", "content": "Hello"}],
    })
    assert r.status_code == 200
    data = r.json()
    assert data["message"]["content"] == "Hi there!"


def test_chat_validation_empty_messages(client):
    r = client.post("/v1/inference/chat", json={
        "messages": [],
    })
    assert r.status_code == 422


def test_chat_llm_error(client, mock_service):
    from src.shared.exceptions import LLMError
    mock_service.chat = AsyncMock(side_effect=LLMError("Timeout"))
    r = client.post("/v1/inference/chat", json={
        "messages": [{"role": "user", "content": "Hi"}],
    })
    assert r.status_code == 503


# ---------------------------------------------------------------------------
# OpenAI-compatible
# ---------------------------------------------------------------------------

def test_openai_chat_endpoint(client):
    r = client.post("/v1/inference/v1/chat/completions", json={
        "messages": [{"role": "user", "content": "Hi"}],
    })
    assert r.status_code == 200
    data = r.json()
    assert data["object"] == "chat.completion"
    assert data["choices"][0]["message"]["content"] == "Hello"
    assert "usage" in data


def test_openai_chat_with_params(client):
    r = client.post("/v1/inference/v1/chat/completions", json={
        "messages": [{"role": "user", "content": "Hi"}],
        "model": "gemma:latest",
        "temperature": 0.1,
        "max_tokens": 100,
    })
    assert r.status_code == 200


def test_openai_chat_llm_error(client, mock_service):
    from src.shared.exceptions import LLMError
    mock_service.openai_chat = AsyncMock(side_effect=LLMError("Error"))
    r = client.post("/v1/inference/v1/chat/completions", json={
        "messages": [{"role": "user", "content": "Hi"}],
    })
    assert r.status_code == 503
