from __future__ import annotations

import asyncio
import json
import time
from typing import Any

import openai
from pydantic import BaseModel

from src.core.settings import get_settings
from src.shared.circuit_breaker import CircuitBreaker
from src.shared.exceptions import LLMError
from src.shared.logger import get_logger
from src.shared.metrics import LLM_LATENCY

logger = get_logger("llm_client")


class LLMClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.model = settings.openai_model
        self._client = openai.AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
        self._breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30.0)

    async def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        retries: int = 3,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        messages: list[dict[str, str]] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        async def _call() -> str:
            start = time.monotonic()
            try:
                kwargs: dict[str, Any] = {
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if response_format is not None:
                    kwargs["response_format"] = response_format
                response = await self._client.chat.completions.create(**kwargs)
                return response.choices[0].message.content or ""
            finally:
                elapsed = time.monotonic() - start
                LLM_LATENCY.observe(elapsed)

        async def _call_with_retry() -> str:
            backoff = 1.0
            last_exc: Exception | None = None
            for attempt in range(retries):
                try:
                    return await _call()
                except (openai.RateLimitError, openai.APITimeoutError) as exc:
                    last_exc = exc
                    logger.warning(
                        "LLM retry %d/%d after error: %s",
                        attempt + 1,
                        retries,
                        exc,
                    )
                    if attempt < retries - 1:
                        await asyncio.sleep(backoff)
                        backoff *= 2
            raise LLMError(f"LLM call failed after {retries} retries") from last_exc

        try:
            return await self._breaker.call(_call_with_retry)
        except Exception as exc:
            if isinstance(exc, LLMError):
                raise
            raise LLMError(str(exc)) from exc

    async def generate_structured(
        self,
        prompt: str,
        response_model: type[BaseModel],
        **kwargs: Any,
    ) -> BaseModel:
        raw = await self.generate(
            prompt,
            response_format={"type": "json_object"},
            **kwargs,
        )
        try:
            data = json.loads(raw)
            return response_model.model_validate(data)
        except (json.JSONDecodeError, Exception) as exc:
            raise LLMError(f"Failed to parse structured response: {exc}") from exc
