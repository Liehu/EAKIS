"""Integration tests for InferenceService with mocked OllamaClient."""
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
def service() -> InferenceService:
    """Create InferenceService with a mocked OllamaClient."""
    with patch("src.inference.service.OllamaClient") as MockClient:
        instance = MockClient.return_value
        instance._default_model = "test-model:latest"
        svc = InferenceService()
        yield svc


# ---------------------------------------------------------------------------
# Pydantic model for structured output tests
# ---------------------------------------------------------------------------


class SampleModel(BaseModel):
    name: str
    score: float


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_check(service: InferenceService) -> None:
    """check_health() returns InferenceHealth with expected fields."""
    service._client.health = AsyncMock(return_value={"version": "0.5.0"})
    service._client.list_models = AsyncMock(return_value=[{"name": "m1"}, {"name": "m2"}])

    result = await service.check_health()

    assert isinstance(result, InferenceHealth)
    assert result.status == "healthy"
    assert result.models_available == 2
    assert result.ollama_version == "0.5.0"
    assert result.latency_ms >= 0


@pytest.mark.asyncio
async def test_list_models(service: InferenceService) -> None:
    """list_models() returns parsed ModelInfo list."""
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
async def test_model_info(service: InferenceService) -> None:
    """model_info() delegates to client and returns raw dict."""
    service._client.model_info = AsyncMock(return_value={
        "license": "MIT",
        "modelfile": "FROM gemma",
        "parameters": "temperature 0.3",
    })

    info = await service.model_info("gemma:latest")

    assert info["license"] == "MIT"
    service._client.model_info.assert_called_once_with("gemma:latest")


@pytest.mark.asyncio
async def test_generate(service: InferenceService) -> None:
    """generate() delegates to client.generate with all parameters."""
    service._client.generate = AsyncMock(return_value={
        "model": "test-model:latest",
        "response": "Generated text",
        "done": True,
    })

    result = await service.generate(
        "Test prompt",
        model="custom",
        system="Be concise",
        temperature=0.5,
        max_tokens=100,
    )

    assert result["response"] == "Generated text"
    service._client.generate.assert_called_once_with(
        "Test prompt",
        model="custom",
        system="Be concise",
        temperature=0.5,
        max_tokens=100,
    )


@pytest.mark.asyncio
async def test_chat(service: InferenceService) -> None:
    """chat() delegates to client.chat."""
    service._client.chat = AsyncMock(return_value={
        "model": "test-model:latest",
        "message": {"role": "assistant", "content": "Hello!"},
        "done": True,
    })

    messages = [{"role": "user", "content": "Hi"}]
    result = await service.chat(
        messages,
        model="custom",
        temperature=0.7,
        max_tokens=200,
    )

    assert result["message"]["content"] == "Hello!"
    service._client.chat.assert_called_once_with(
        messages,
        model="custom",
        temperature=0.7,
        max_tokens=200,
    )


@pytest.mark.asyncio
async def test_openai_chat(service: InferenceService) -> None:
    """openai_chat() delegates to client.openai_chat."""
    service._client.openai_chat = AsyncMock(return_value={
        "id": "chatcmpl-123",
        "choices": [{"message": {"role": "assistant", "content": "Hi"}}],
    })

    messages = [{"role": "user", "content": "Hello"}]
    result = await service.openai_chat(
        messages,
        model="custom",
        temperature=0.4,
        max_tokens=2048,
    )

    assert result["choices"][0]["message"]["content"] == "Hi"
    service._client.openai_chat.assert_called_once_with(
        messages,
        model="custom",
        temperature=0.4,
        max_tokens=2048,
    )


@pytest.mark.asyncio
async def test_structured_output(service: InferenceService) -> None:
    """generate_structured() returns validated Pydantic model."""
    service._client.generate = AsyncMock(return_value={
        "response": '{"name": "test", "score": 0.95}',
        "done": True,
    })

    result = await service.generate_structured("Generate test data", SampleModel)

    assert isinstance(result, SampleModel)
    assert result.name == "test"
    assert result.score == 0.95


@pytest.mark.asyncio
async def test_structured_output_retry(service: InferenceService) -> None:
    """generate_structured() retries on invalid JSON and succeeds on second attempt."""
    call_count = 0

    async def mock_generate(*args: Any, **kwargs: Any) -> dict[str, Any]:
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"response": "NOT VALID JSON", "done": True}
        return {"response": '{"name": "test", "score": 0.5}', "done": True}

    service._client.generate = mock_generate

    result = await service.generate_structured("Generate", SampleModel, retries=1)

    assert isinstance(result, SampleModel)
    assert result.name == "test"
    assert result.score == 0.5
    assert call_count == 2
