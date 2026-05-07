"""Lightweight in-process event bus with sync and async handler support."""

import asyncio
import inspect
from collections.abc import Callable
from typing import Any

from src.shared.logger import get_logger

_logger = get_logger("event_bus")


class EventBus:
    """Publish / subscribe event bus that accepts both sync and async handlers."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[..., Any]]] = {}

    def subscribe(self, event_type: str, handler: Callable[..., Any]) -> None:
        """Register *handler* for *event_type*."""
        self._subscribers.setdefault(event_type, []).append(handler)

    def unsubscribe(self, event_type: str, handler: Callable[..., Any]) -> bool:
        """Remove *handler* from *event_type*.  Return True if removed."""
        handlers = self._subscribers.get(event_type)
        if handlers is None:
            return False
        try:
            handlers.remove(handler)
        except ValueError:
            return False
        if not handlers:
            del self._subscribers[event_type]
        return True

    async def publish(self, event_type: str, payload: Any) -> None:
        """Dispatch *payload* to every registered handler for *event_type*.

        Async handlers are gathered concurrently via ``asyncio.gather``.
        Sync handlers are called directly.  Errors are caught and logged so
        that one failing handler does not block the rest.
        """
        handlers = list(self._subscribers.get(event_type, []))
        if not handlers:
            return

        sync_results: list[None] = []
        async_coros: list[Any] = []

        for handler in handlers:
            if inspect.iscoroutinefunction(handler):
                async_coros.append(self._safe_async(handler, event_type, payload))
            else:
                sync_results.append(self._safe_sync(handler, event_type, payload))

        if async_coros:
            await asyncio.gather(*async_coros)

    # -- private helpers ------------------------------------------------------

    @staticmethod
    def _safe_sync(handler: Callable[..., Any], event_type: str, payload: Any) -> None:
        try:
            handler(payload)
        except Exception:
            _logger.exception("Sync handler %r failed for event %r", handler, event_type)

    @staticmethod
    async def _safe_async(handler: Callable[..., Any], event_type: str, payload: Any) -> None:
        try:
            await handler(payload)
        except Exception:
            _logger.exception("Async handler %r failed for event %r", handler, event_type)


# -- Module-level singleton and convenience delegates -------------------------

_event_bus = EventBus()


def get_event_bus() -> EventBus:
    """Return the module-level EventBus singleton."""
    return _event_bus


def subscribe(event_type: str, handler: Callable[..., Any]) -> None:
    """Register *handler* on the default EventBus."""
    _event_bus.subscribe(event_type, handler)


def unsubscribe(event_type: str, handler: Callable[..., Any]) -> bool:
    """Remove *handler* from the default EventBus."""
    return _event_bus.unsubscribe(event_type, handler)


async def publish(event_type: str, payload: Any) -> None:
    """Publish *payload* on the default EventBus."""
    await _event_bus.publish(event_type, payload)
