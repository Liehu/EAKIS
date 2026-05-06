import functools
from collections.abc import Callable
from typing import Any


def cache(ttl: int = 300) -> Callable[..., Any]:
    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            # TODO: implement TTL-based caching
            return await func(*args, **kwargs)
        return wrapper
    return decorator
