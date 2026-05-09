"""Inference service — orchestrates Ollama client and integrates with LLMClient."""

from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel

from src.inference.client import OllamaClient
from src.shared.exceptions import LLMError
from src.shared.logger import get_logger

logger = get_logger("inference_service")


class ModelInfo(BaseModel):
    name: str
    size: int = 0
    quantization: str = ""
    family: str = ""
    parameter_size: str = ""
    format: str = ""


class InferenceHealth(BaseModel):
    status: str
    ollama_version: str = ""
    default_model: str = ""
    models_available: int = 0
    latency_ms: float = 0.0


class InferenceService:
    """High-level inference service wrapping Ollama.

    Provides:
    - Health checks
    - Model listing / info
    - Text generation (Ollama native + OpenAI-compatible)
    - Chat completion
    - Structured output via JSON generation
    """

    def __init__(self) -> None:
        self._client = OllamaClient()

    # -- health ----------------------------------------------------------------

    async def check_health(self) -> InferenceHealth:
        start = time.monotonic()
        try:
            info = await self._client.health()
            models = await self._client.list_models()
            elapsed_ms = (time.monotonic() - start) * 1000
            return InferenceHealth(
                status="healthy",
                ollama_version=info.get("version", "unknown"),
                default_model=self._client._default_model,
                models_available=len(models),
                latency_ms=round(elapsed_ms, 1),
            )
        except Exception as exc:
            logger.error("Inference health check failed: %s", exc)
            return InferenceHealth(status="unhealthy")

    # -- model management ------------------------------------------------------

    async def list_models(self) -> list[ModelInfo]:
        raw = await self._client.list_models()
        result: list[ModelInfo] = []
        for m in raw:
            details = m.get("details", {})
            result.append(ModelInfo(
                name=m.get("name", ""),
                size=m.get("size", 0),
                quantization=details.get("quantization_level", ""),
                family=details.get("family", ""),
                parameter_size=details.get("parameter_size", ""),
                format=details.get("format", ""),
            ))
        return result

    async def model_info(self, name: str) -> dict[str, Any]:
        return await self._client.model_info(name)

    # -- generate --------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        return await self._client.generate(
            prompt,
            model=model,
            system=system,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # -- chat ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> dict[str, Any]:
        return await self._client.chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # -- structured output -----------------------------------------------------

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[BaseModel],
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float = 0.1,
        max_tokens: int | None = None,
        retries: int = 2,
    ) -> BaseModel:
        """Generate a structured response validated against a Pydantic model.

        Instructs the model to output JSON, then validates against the schema.
        """
        json_schema = response_model.model_json_schema()
        sys_prompt = (
            (system + "\n\n" if system else "")
            + "You MUST respond with valid JSON matching this schema:\n"
            + __import__("json").dumps(json_schema, indent=2)
            + "\nDo NOT include any text outside the JSON object."
        )

        last_exc: Exception | None = None
        for attempt in range(retries + 1):
            try:
                result = await self._client.generate(
                    prompt,
                    model=model,
                    system=sys_prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                raw = result.get("response", "")
                import json
                # Strip markdown code fences if present
                if "```" in raw:
                    raw = raw.split("```")[1]
                    if raw.startswith("json"):
                        raw = raw[4:]
                    raw = raw.strip()
                data = json.loads(raw)
                return response_model.model_validate(data)
            except Exception as exc:
                last_exc = exc
                logger.warning("Structured generation attempt %d failed: %s", attempt + 1, exc)

        raise LLMError(f"Structured generation failed after {retries + 1} attempts: {last_exc}") from last_exc

    # -- OpenAI-compatible -----------------------------------------------------

    async def openai_chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        return await self._client.openai_chat(
            messages,
            model=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

    # -- convenience accessor --------------------------------------------------

    @property
    def client(self) -> OllamaClient:
        return self._client


_service: InferenceService | None = None


def get_inference_service() -> InferenceService:
    global _service
    if _service is None:
        _service = InferenceService()
    return _service
