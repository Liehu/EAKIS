"""Ollama REST API client for local LLM inference."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any, AsyncIterator

import httpx

from src.core.settings import get_settings
from src.shared.circuit_breaker import CircuitBreaker
from src.shared.exceptions import LLMError
from src.shared.logger import get_logger
from src.shared.metrics import LLM_LATENCY, INFERENCE_REQUEST_COUNT

logger = get_logger("inference_client")


class OllamaClient:
    """Async client for Ollama REST API (http://localhost:11434).

    Supports:
    - /api/generate  — text generation
    - /api/chat      — chat completion
    - /api/tags      — list local models
    - /api/show      — model details
    - /api/pull      — pull a model
    """

    def __init__(self) -> None:
        settings = get_settings()
        self._base_url = settings.ollama_base_url.rstrip("/")
        self._default_model = settings.ollama_default_model
        self._timeout = settings.ollama_request_timeout
        self._num_ctx = settings.ollama_num_ctx
        self._num_predict = settings.ollama_num_predict
        self._breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=30.0)

    def _http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            timeout=httpx.Timeout(self._timeout, connect=10.0),
        )

    # -- health check ----------------------------------------------------------

    async def health(self) -> dict[str, Any]:
        async with self._http() as c:
            r = await c.get("/")
            r.raise_for_status()
            return r.json()

    # -- model management ------------------------------------------------------

    async def list_models(self) -> list[dict[str, Any]]:
        async with self._http() as c:
            r = await c.get("/api/tags")
            r.raise_for_status()
            return r.json().get("models", [])

    async def model_info(self, name: str) -> dict[str, Any]:
        async with self._http() as c:
            r = await c.post("/api/show", json={"name": name})
            r.raise_for_status()
            return r.json()

    async def pull_model(self, name: str) -> dict[str, Any]:
        async with self._http() as c:
            r = await c.post("/api/pull", json={"name": name, "stream": False})
            r.raise_for_status()
            return r.json()

    # -- generate --------------------------------------------------------------

    async def generate(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        context: list[int] | None = None,
        retries: int = 3,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model or self._default_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_ctx": self._num_ctx,
                "num_predict": max_tokens or self._num_predict,
                "temperature": temperature if temperature is not None else 0.3,
            },
        }
        if system:
            body["system"] = system
        if context:
            body["context"] = context

        async def _call() -> dict[str, Any]:
            start = time.monotonic()
            async with self._http() as c:
                r = await c.post("/api/generate", json=body)
                r.raise_for_status()
                elapsed = time.monotonic() - start
                LLM_LATENCY.observe(elapsed)
                INFERENCE_REQUEST_COUNT.labels(endpoint="generate").inc()
                return r.json()

        return await self._retry(_call, retries)

    # -- chat ------------------------------------------------------------------

    async def chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        retries: int = 3,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {
            "model": model or self._default_model,
            "messages": messages,
            "stream": False,
            "options": {
                "num_ctx": self._num_ctx,
                "num_predict": max_tokens or self._num_predict,
                "temperature": temperature if temperature is not None else 0.3,
            },
        }

        async def _call() -> dict[str, Any]:
            start = time.monotonic()
            async with self._http() as c:
                r = await c.post("/api/chat", json=body)
                r.raise_for_status()
                elapsed = time.monotonic() - start
                LLM_LATENCY.observe(elapsed)
                INFERENCE_REQUEST_COUNT.labels(endpoint="chat").inc()
                return r.json()

        return await self._retry(_call, retries)

    # -- streaming generate ----------------------------------------------------

    async def generate_stream(
        self,
        prompt: str,
        *,
        model: str | None = None,
        system: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
    ) -> AsyncIterator[str]:
        body: dict[str, Any] = {
            "model": model or self._default_model,
            "prompt": prompt,
            "stream": True,
            "options": {
                "num_ctx": self._num_ctx,
                "num_predict": max_tokens or self._num_predict,
                "temperature": temperature if temperature is not None else 0.3,
            },
        }
        if system:
            body["system"] = system

        async with self._http() as c:
            async with c.stream("POST", "/api/generate", json=body) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.strip():
                        continue
                    chunk = json.loads(line)
                    if chunk.get("response"):
                        yield chunk["response"]
                    if chunk.get("done"):
                        break

    # -- OpenAI-compatible endpoint -------------------------------------------

    async def openai_chat(
        self,
        messages: list[dict[str, str]],
        *,
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
    ) -> dict[str, Any]:
        """Call Ollama's /v1/chat/completions (OpenAI-compatible)."""
        body: dict[str, Any] = {
            "model": model or self._default_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False,
        }

        async def _call() -> dict[str, Any]:
            start = time.monotonic()
            async with self._http() as c:
                r = await c.post("/v1/chat/completions", json=body)
                r.raise_for_status()
                elapsed = time.monotonic() - start
                LLM_LATENCY.observe(elapsed)
                INFERENCE_REQUEST_COUNT.labels(endpoint="openai_chat").inc()
                return r.json()

        return await self._retry(_call, retries=3)

    # -- helpers ---------------------------------------------------------------

    async def _retry(
        self, fn: Any, retries: int, backoff_base: float = 1.0
    ) -> Any:
        last_exc: Exception | None = None
        backoff = backoff_base
        for attempt in range(retries):
            try:
                return await self._breaker.call(fn)
            except Exception as exc:
                last_exc = exc
                if attempt < retries - 1:
                    logger.warning("Ollama retry %d/%d: %s", attempt + 1, retries, exc)
                    await asyncio.sleep(backoff)
                    backoff *= 2
        raise LLMError(f"Ollama call failed after {retries} retries: {last_exc}") from last_exc
