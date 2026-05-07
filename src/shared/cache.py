"""TTL-based in-memory cache and async decorator."""

import functools
import time
from collections.abc import Callable
from typing import Any


class TTLCache:
    """Simple dictionary-backed cache with per-entry time-to-live."""

    DEFAULT_TTL: int = 300  # seconds

    def __init__(self) -> None:
        self._store: dict[str, tuple[Any, float]] = {}

    def get(self, key: str) -> Any | None:
        """Return cached value if present and not expired, else None."""
        entry = self._store.get(key)
        if entry is None:
            return None
        value, expiry = entry
        if time.monotonic() >= expiry:
            del self._store[key]
            return None
        return value

    def set(self, key: str, value: Any, ttl: int | None = None) -> None:
        """Store *value* under *key* with the given TTL (default 300 s)."""
        effective_ttl = ttl if ttl is not None else self.DEFAULT_TTL
        self._store[key] = (value, time.monotonic() + effective_ttl)

    def delete(self, key: str) -> bool:
        """Remove *key* from the cache.  Return True if it was present."""
        return self._store.pop(key, None) is not None

    def clear(self) -> None:
        """Remove every entry regardless of expiry."""
        self._store.clear()

    def _cleanup(self) -> int:
        """Remove all expired entries and return the count purged."""
        now = time.monotonic()
        expired = [k for k, (_, exp) in self._store.items() if now >= exp]
        for key in expired:
            del self._store[key]
        return len(expired)


# -- Module-level singleton --------------------------------------------------

_default_cache = TTLCache()


def cache(ttl: int = 300) -> Callable[..., Any]:
    """Decorator that memoises an async function's return value with a TTL."""

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            cache_key = (
                f"{func.__module__}.{func.__qualname__}"
                f":{args!r}:{sorted(kwargs.items())!r}"
            )
            cached = _default_cache.get(cache_key)
            if cached is not None:
                return cached
            result = await func(*args, **kwargs)
            _default_cache.set(cache_key, result, ttl=ttl)
            return result

        return wrapper

    return decorator
