from collections import defaultdict
from collections.abc import Callable
from typing import Any


class EventBus:
    def __init__(self) -> None:
        self._subscribers: dict[str, list[Callable[..., Any]]] = defaultdict(list)

    def subscribe(self, event_type: str, handler: Callable[..., Any]) -> None:
        self._subscribers[event_type].append(handler)

    async def publish(self, event_type: str, payload: Any) -> None:
        for handler in self._subscribers.get(event_type, []):
            await handler(payload)
