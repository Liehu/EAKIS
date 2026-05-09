"""Anti-crawl middleware — 统一管理代理轮换、UA 轮换、请求限速.

将 ProxyPool 和 AntiCrawlProfile 组合为 CrawlerAgent 可直接使用的中间件层。
"""

from __future__ import annotations

import asyncio
import logging
import time

from src.intelligence.anti_crawl.proxy_pool import ProxyEntry, ProxyPool
from src.intelligence.anti_crawl.ua_pool import AntiCrawlProfile, BrowserProfile
from src.intelligence.config import AntiCrawlConfig

logger = logging.getLogger("eakis.intelligence.middleware")


class AntiCrawlMiddleware:
    """反爬中间件 — 每次请求前获取伪装上下文。

    用法:
        mw = AntiCrawlMiddleware(config)
        await mw.initialize()
        ctx = await mw.before_request(source_id="fofa")
        # 使用 ctx.proxy, ctx.headers, ctx.profile
        await mw.after_request(ctx, success=True, latency=0.5)
    """

    def __init__(self, config: AntiCrawlConfig | None = None) -> None:
        self.config = config or AntiCrawlConfig()
        self.proxy_pool = ProxyPool(
            pool_size=self.config.proxy_pool_size,
            health_check_interval=300,
            check_timeout=5.0,
        )
        self.profile = AntiCrawlProfile(pool_size=self.config.ua_pool_size)
        self._source_last_request: dict[str, float] = {}
        self._initialized = False

    async def initialize(self, seed_proxies: list[str] | None = None) -> None:
        if self.config.proxy_rotation:
            count = await self.proxy_pool.initialize(seed_proxies)
            logger.info("代理池就绪: %d 个代理", count)
        self._initialized = True

    async def before_request(self, source_id: str = "") -> RequestContext:
        """请求前调用：获取代理、UA、限速等待。"""
        # 1. 限速等待
        await self._rate_limit(source_id)

        # 2. 获取代理
        proxy: ProxyEntry | None = None
        if self.config.proxy_rotation:
            proxy = await self.proxy_pool.acquire()

        # 3. 获取浏览器伪装
        browser_profile: BrowserProfile | None = None
        headers: dict[str, str] = {}
        if self.config.ua_rotation:
            browser_profile = self.profile.next_profile()
            headers = {
                "User-Agent": browser_profile.user_agent,
                "Accept-Language": browser_profile.accept_language,
                "Accept-Encoding": browser_profile.accept_encoding,
            }

        # 4. 记录请求时间
        self._source_last_request[source_id] = time.monotonic()

        return RequestContext(
            source_id=source_id,
            proxy=proxy,
            profile=browser_profile,
            headers=headers,
            started_at=time.monotonic(),
        )

    async def after_request(self, ctx: RequestContext, success: bool = True) -> None:
        """请求后调用：报告代理使用结果。"""
        if ctx.proxy and self.config.proxy_rotation:
            latency = time.monotonic() - ctx.started_at
            await self.proxy_pool.report(ctx.proxy.address, success=success, latency=latency)

    async def _rate_limit(self, source_id: str) -> None:
        if not self.config.proxy_rotation and not self.config.ua_rotation:
            delay = 0.0
        else:
            import random
            delay = random.uniform(self.config.request_delay_min, self.config.request_delay_max)

        last = self._source_last_request.get(source_id, 0.0)
        elapsed = time.monotonic() - last
        if delay > 0 and elapsed < delay:
            await asyncio.sleep(delay - elapsed)

    async def get_stats(self) -> dict:
        stats: dict = {
            "ua_pool_size": self.profile.ua_pool.size,
            "initialized": self._initialized,
        }
        if self.config.proxy_rotation:
            stats["proxy"] = await self.proxy_pool.get_stats()
        return stats


class RequestContext:
    """单次请求的反爬上下文。"""

    __slots__ = ("source_id", "proxy", "profile", "headers", "started_at")

    def __init__(
        self,
        source_id: str = "",
        proxy: ProxyEntry | None = None,
        profile: BrowserProfile | None = None,
        headers: dict[str, str] | None = None,
        started_at: float = 0.0,
    ) -> None:
        self.source_id = source_id
        self.proxy = proxy
        self.profile = profile
        self.headers = headers or {}
        self.started_at = started_at
