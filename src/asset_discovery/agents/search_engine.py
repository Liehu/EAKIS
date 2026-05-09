from __future__ import annotations

import asyncio
import logging
import time

from src.asset_discovery.config import RATE_LIMITS, SearchConfig
from src.asset_discovery.models import RawAsset
from src.asset_discovery.services.base import BaseSearchClient

logger = logging.getLogger("eakis.asset_discovery.search")


class TokenBucket:
    def __init__(self, capacity: float, refill_rate: float) -> None:
        self.capacity = capacity
        self.refill_rate = refill_rate
        self._tokens: float = capacity
        self._last_refill: float = time.monotonic()

    async def acquire(self) -> None:
        self._refill()
        if self._tokens >= 1.0:
            self._tokens -= 1.0
            return
        wait = (1.0 - self._tokens) / self.refill_rate
        await asyncio.sleep(wait)
        self._tokens = 0.0

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self.capacity, self._tokens + elapsed * self.refill_rate)
        self._last_refill = now


class AssetSearchAgent:
    def __init__(
        self,
        search_client: BaseSearchClient,
        config: SearchConfig | None = None,
    ) -> None:
        self.search_client = search_client
        self.config = config or SearchConfig()
        self._limiters: dict[str, TokenBucket] = {}
        for platform in self.config.platforms:
            limits = RATE_LIMITS.get(platform, {"requests_per_minute": 5.0})
            rpm = limits.get("requests_per_minute", 5.0)
            self._limiters[platform] = TokenBucket(
                capacity=rpm, refill_rate=rpm / 60.0
            )

    async def search(
        self,
        dsl_queries: list[dict[str, str]],
        platforms: list[str] | None = None,
    ) -> list[RawAsset]:
        effective_platforms = platforms or self.config.platforms
        all_assets: list[RawAsset] = []
        seen_keys: set[str] = set()

        tasks = []
        for platform in effective_platforms:
            limiter = self._limiters.get(platform)
            for query_dict in dsl_queries:
                platform_name = query_dict.get("platform", "")
                query_str = query_dict.get("query", "")
                if platform_name and platform_name.lower() != platform.lower():
                    continue
                if not query_str:
                    continue
                tasks.append(self._search_single(platform, query_str, limiter))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.warning("Search failed: %s", result)
                continue
            for asset in result:
                if self.config.deduplicate:
                    key = asset.dedup_key
                    if key in seen_keys:
                        continue
                    seen_keys.add(key)
                all_assets.append(asset)

        logger.info("Asset search completed: %d unique assets", len(all_assets))
        return all_assets

    async def _search_single(
        self,
        platform: str,
        query: str,
        limiter: TokenBucket | None,
    ) -> list[RawAsset]:
        if limiter:
            await limiter.acquire()
        return await self.search_client.search(
            platform=platform,
            query=query,
            page_size=self.config.page_size,
            max_pages=self.config.max_pages,
        )
