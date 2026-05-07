"""Circuit-breaker pattern with CLOSED / OPEN / HALF_OPEN states."""

import time
from collections.abc import Callable
from enum import Enum, unique
from typing import Any

from src.shared.exceptions import CircuitOpenError


@unique
class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


class CircuitBreaker:
    """Protects a resource by opening the circuit after repeated failures.

    Parameters
    ----------
    failure_threshold:
        Number of consecutive failures before the circuit opens.
    recovery_timeout:
        Seconds to wait in OPEN state before transitioning to HALF_OPEN.
    expected_exception:
        Exception base type that counts as a failure.  Other exceptions
        propagate immediately without affecting the state machine.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type[Exception] = Exception,
    ) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self._failure_count: int = 0
        self._last_failure_time: float = 0.0
        self._state: CircuitState = CircuitState.CLOSED

    # -- public API -----------------------------------------------------------

    @property
    def state(self) -> CircuitState:
        """Current circuit state (read-only for callers)."""
        return self._state

    async def call(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        """Execute *func* through the circuit-breaker state machine."""
        if self._state is CircuitState.CLOSED:
            return await self._call_closed(func, *args, **kwargs)

        if self._state is CircuitState.OPEN:
            return await self._call_open(func, *args, **kwargs)

        # HALF_OPEN
        return await self._call_half_open(func, *args, **kwargs)

    # -- private helpers ------------------------------------------------------

    async def _call_closed(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        try:
            result = await func(*args, **kwargs)
        except self.expected_exception:
            self._failure_count += 1
            self._last_failure_time = time.monotonic()
            if self._failure_count >= self.failure_threshold:
                self._state = CircuitState.OPEN
            raise
        self._failure_count = 0
        return result

    async def _call_open(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        elapsed = time.monotonic() - self._last_failure_time
        if elapsed < self.recovery_timeout:
            raise CircuitOpenError("Circuit breaker is open")
        self._state = CircuitState.HALF_OPEN
        return await self._call_half_open(func, *args, **kwargs)

    async def _call_half_open(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        try:
            result = await func(*args, **kwargs)
        except self.expected_exception:
            self._last_failure_time = time.monotonic()
            self._state = CircuitState.OPEN
            raise
        self._failure_count = 0
        self._state = CircuitState.CLOSED
        return result
