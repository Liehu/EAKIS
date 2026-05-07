"""内存令牌桶限流中间件."""

from __future__ import annotations

import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.types import ASGIApp

from src.core.settings import get_settings

_SKIP_PATHS = {"/v1/health", "/docs", "/openapi.json", "/v1/openapi.json", "/redoc"}


class TokenBucket:
    __slots__ = ("capacity", "tokens", "refill_rate", "last_refill")

    def __init__(self, capacity: int, refill_rate: float) -> None:
        self.capacity = capacity
        self.tokens = float(capacity)
        self.refill_rate = refill_rate
        self.last_refill = time.monotonic()

    def consume(self, n: int = 1) -> bool:
        self._refill()
        if self.tokens >= n:
            self.tokens -= n
            return True
        return False

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.capacity, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now


class RateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, rpm: int | None = None) -> None:
        super().__init__(app)
        settings = get_settings()
        self.rpm = rpm or settings.rate_limit_rpm
        self._buckets: dict[str, TokenBucket] = defaultdict(
            lambda: TokenBucket(capacity=self.rpm, refill_rate=self.rpm / 60.0)
        )

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        client_id = request.client.host if request.client else "unknown"
        bucket = self._buckets[client_id]

        if not bucket.consume():
            return Response(
                content='{"detail":"Rate limit exceeded"}',
                status_code=429,
                media_type="application/json",
            )

        return await call_next(request)
