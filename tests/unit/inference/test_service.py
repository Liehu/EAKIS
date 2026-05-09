"""Unit tests for InferenceService."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from src.inference.service import InferenceService, InferenceHealth, ModelInfo
from src.shared.exceptions import LLMError


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_client():
    client = MagicMock()
    return client


@pytest.fixture
def service():
    with patch("src.inference.service.OllamaClient") as MockClient:
        instance = MockClient.return_value
        instance._default_model = "test-model:latest"
        svc = InferenceService()
        yield svc


# ---------------------------------------------------------------------------
# Health check
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_health_healthy(service):
    service._client.health = AsyncMock(return_value={"version": "0.5.0"})
    service._client.list_models = AsyncMock(return_value=[{"name": "m1"}, {"name": "m2"}])
    result = await service.check_health()
    assert result.status == "healthy"
    assert result.models_available == 2
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_health_unhealthy(service):
    service._client.health = AsyncMock(side_effect=Exception("Cannot connect"))
    result = await service.check_health()
    assert result.status == "unhealthy"


# ---------------------------------------------------------------------------
# Model listing
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_list_models(service):
    service._client.list_models = AsyncMock(return_value=[
        {
            "name": "gemma:latest",
            "size": 4700000000,
            "details": {
                "family": "gemma",
                "parameter_size": "4B",
                "quantization_level": "Q4_K_M",
                "format": "gguf",
            },
        }
    ])
    models = await service.list_models()
    assert len(models) == 1
    assert isinstance(models[0], ModelInfo)
    assert models[0].name == "gemma:latest"
    assert models[0].family == "gemma"
    assert models[0].parameter_size == "4B"


@pytest.mark.asyncio
async def test_list_models_empty(service):
    service._client.list_models = AsyncMock(return_value=[])
    models = await service.list_models()
    assert models == []


# ---------------------------------------------------------------------------
# Model info
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_model_info(service):
    service._client.model_info = AsyncMock(return_value={
        "license": "MIT",
        "modelfile": "FROM gemma",
        "parameters": "temperature 0.3",
    })
    info = await service.model_info("gemma:latest")
    assert info["license"] == "MIT"


# ---------------------------------------------------------------------------
# Generate
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_generate(service):
    service._client.generate = AsyncMock(return_value={
        "model": "gemma:latest",
        "response": "Generated text",
        "done": True,
    })
    result = await service.generate("Test prompt")
    assert result["response"] == "Generated text"


@pytest.mark.asyncio
async def test_generate_with_params(service):
    service._client.generate = AsyncMock(return_value={
        "model": "custom",
        "response": "Custom output",
        "done": True,
    })
    result = await service.generate(
        "Test",
        model="custom",
        system="Be concise",
        temperature=0.5,
        max_tokens=100,
    )
    service._client.generate.assert_called_once_with(
        "Test",
        model="custom",
        system="Be concise",
        temperature=0.5,
        max_tokens=100,
    )


# ---------------------------------------------------------------------------
# Chat
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_chat(service):
    service._client.chat = AsyncMock(return_value={
        "model": "gemma:latest",
        "message": {"role": "assistant", "content": "Hello!"},
        "done": True,
    })
    result = await service.chat([{"role": "user", "content": "Hi"}])
    assert result["message"]["content"] == "Hello!"


# ---------------------------------------------------------------------------
# Structured output
# ---------------------------------------------------------------------------

class TestModel(BaseModel):
    name: str
    score: float


@pytest.mark.asyncio
async def test_generate_structured(service):
    service._client.generate = AsyncMock(return_value={
        "response": '{"name": "test", "score": 0.95}',
        "done": True,
    })
    result = await service.generate_structured("Generate test data", TestModel)
    assert isinstance(result, TestModel)
    assert result.name == "test"
    assert result.score == 0.95


@pytest.mark.asyncio
async def test_generate_structured_with_markdown_fences(service):
    service._client.generate = AsyncMock(return_value={
        "response": '```json\n{"name": "test", "score": 0.9}\n```',
        "done": True,
    })
    result = await service.generate_structured("Generate", TestModel)
    assert result.name == "test"


@pytest.mark.asyncio
async def test_generate_structured_retries(service):
    # First call fails, second succeeds
    call_count = 0

    async def mock_generate(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"response": "NOT JSON", "done": True}
        return {"response": '{"name": "test", "score": 0.5}', "done": True}

    service._client.generate = mock_generate
    result = await service.generate_structured("Generate", TestModel, retries=1)
    assert result.name == "test"
    assert call_count == 2


@pytest.mark.asyncio
async def test_generate_structured_all_retries_fail(service):
    service._client.generate = AsyncMock(return_value={"response": "NOT JSON", "done": True})
    with pytest.raises(LLMError, match="Structured generation failed"):
        await service.generate_structured("Generate", TestModel, retries=1)


# ---------------------------------------------------------------------------
# OpenAI-compatible
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_openai_chat(service):
    service._client.openai_chat = AsyncMock(return_value={
        "id": "chatcmpl-123",
        "choices": [{"message": {"role": "assistant", "content": "Hi"}}],
    })
    result = await service.openai_chat([{"role": "user", "content": "Hi"}])
    assert result["choices"][0]["message"]["content"] == "Hi"


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

def test_get_inference_service_singleton():
    from src.inference.service import get_inference_service, _service
    # Reset singleton
    import src.inference.service as svc_mod
    svc_mod._service = None

    s1 = get_inference_service()
    s2 = get_inference_service()
    assert s1 is s2

    # Cleanup
    svc_mod._service = None
