"""Infrastructure integration tests: shared components (event bus, circuit breaker, cache)."""

from __future__ import annotations

import asyncio
import time

import pytest

from src.shared.cache import TTLCache
from src.shared.circuit_breaker import CircuitBreaker, CircuitState
from src.shared.event_bus import EventBus
from src.shared.exceptions import CircuitOpenError


class TestEventBus:
    @pytest.mark.asyncio
    async def test_sync_handler(self):
        bus = EventBus()
        received = []
        bus.subscribe("test.event", lambda payload: received.append(payload))
        await bus.publish("test.event", {"key": "value"})
        assert len(received) == 1
        assert received[0] == {"key": "value"}

    @pytest.mark.asyncio
    async def test_async_handler(self):
        bus = EventBus()
        received = []

        async def handler(payload):
            received.append(payload)

        bus.subscribe("test.event", handler)
        await bus.publish("test.event", "hello")
        assert received == ["hello"]

    @pytest.mark.asyncio
    async def test_unsubscribe(self):
        bus = EventBus()
        received = []

        def handler(payload):
            received.append(payload)

        bus.subscribe("test.event", handler)
        bus.unsubscribe("test.event", handler)
        await bus.publish("test.event", "data")
        assert len(received) == 0

    @pytest.mark.asyncio
    async def test_error_isolation(self):
        """One failing handler should not block others."""
        bus = EventBus()
        call_log = []

        def bad_handler(payload):
            raise RuntimeError("boom")

        def good_handler(payload):
            call_log.append(payload)

        bus.subscribe("test.event", bad_handler)
        bus.subscribe("test.event", good_handler)
        await bus.publish("test.event", "data")
        assert call_log == ["data"]


class TestCircuitBreaker:
    @pytest.mark.asyncio
    async def test_closed_passes_through(self):
        cb = CircuitBreaker(failure_threshold=3)
        result = await cb.call(asyncio.coroutine(lambda: "ok") if False else self._ok)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.asyncio
    async def test_opens_after_threshold(self):
        cb = CircuitBreaker(failure_threshold=3, expected_exception=ValueError)

        async def fail():
            raise ValueError("fail")

        for _ in range(3):
            with pytest.raises(ValueError):
                await cb.call(fail)
        assert cb.state == CircuitState.OPEN

        with pytest.raises(CircuitOpenError):
            await cb.call(self._ok)

    @pytest.mark.asyncio
    async def test_half_open_to_closed(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.05, expected_exception=ValueError)

        async def fail():
            raise ValueError("fail")

        # Trip to OPEN
        for _ in range(2):
            with pytest.raises(ValueError):
                await cb.call(fail)
        assert cb.state == CircuitState.OPEN

        # Wait for recovery
        await asyncio.sleep(0.06)

        # One success should close
        result = await cb.call(self._ok)
        assert result == "ok"
        assert cb.state == CircuitState.CLOSED

    @staticmethod
    async def _ok():
        return "ok"


class TestTTLCache:
    def test_set_get(self):
        cache = TTLCache()
        cache.set("k", "v", ttl=60)
        assert cache.get("k") == "v"

    def test_expired_returns_none(self):
        cache = TTLCache()
        cache.set("k", "v", ttl=0)
        time.sleep(0.01)
        assert cache.get("k") is None

    def test_delete(self):
        cache = TTLCache()
        cache.set("k", "v")
        assert cache.delete("k") is True
        assert cache.get("k") is None
        assert cache.delete("k") is False

    def test_cleanup(self):
        cache = TTLCache()
        cache.set("a", 1, ttl=0)
        cache.set("b", 2, ttl=0)
        cache.set("c", 3, ttl=60)
        time.sleep(0.01)
        purged = cache._cleanup()
        assert purged == 2
        assert cache.get("a") is None
        assert cache.get("c") == 3

    def test_clear(self):
        cache = TTLCache()
        cache.set("a", 1)
        cache.set("b", 2)
        cache.clear()
        assert cache.get("a") is None
        assert cache.get("b") is None
