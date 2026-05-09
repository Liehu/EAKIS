"""Unit tests for anti-crawl components: ProxyPool, UAPool, Fingerprint, Middleware."""

import pytest

from src.intelligence.anti_crawl.middleware import AntiCrawlMiddleware, RequestContext
from src.intelligence.anti_crawl.proxy_pool import InMemoryProxyStore, ProxyEntry, ProxyPool
from src.intelligence.anti_crawl.ua_pool import (
    AntiCrawlProfile,
    BrowserProfile,
    FingerprintGenerator,
    UAPool,
)
from src.intelligence.config import AntiCrawlConfig, CrawlConfig
from src.intelligence.models import CollectionStatus, DataSource, DslQuery, RawDocument, SourceCategory
from src.intelligence.agents.crawler import CrawlerAgent
from src.intelligence.services.base import BaseScraper


# ---------------------------------------------------------------------------
# ProxyPool tests
# ---------------------------------------------------------------------------


class TestProxyEntry:
    def test_url_http(self):
        e = ProxyEntry(address="1.2.3.4:8080", protocol="http")
        assert e.url == "http://1.2.3.4:8080"

    def test_url_socks5(self):
        e = ProxyEntry(address="5.6.7.8:1080", protocol="socks5")
        assert e.url == "socks5://5.6.7.8:1080"

    def test_is_healthy_default(self):
        e = ProxyEntry(address="1.2.3.4:8080")
        assert e.is_healthy is True

    def test_is_healthy_too_many_fails(self):
        e = ProxyEntry(address="1.2.3.4:8080", fail_count=3)
        assert e.is_healthy is False

    def test_is_healthy_low_score(self):
        e = ProxyEntry(address="1.2.3.4:8080", score=0.1)
        assert e.is_healthy is False


class TestInMemoryProxyStore:
    @pytest.mark.asyncio
    async def test_add_and_get_all(self):
        store = InMemoryProxyStore()
        await store.add(ProxyEntry(address="1.2.3.4:8080"))
        await store.add(ProxyEntry(address="5.6.7.8:3128"))
        entries = await store.get_all()
        assert len(entries) == 2

    @pytest.mark.asyncio
    async def test_remove(self):
        store = InMemoryProxyStore()
        await store.add(ProxyEntry(address="1.2.3.4:8080"))
        await store.remove("1.2.3.4:8080")
        assert await store.count() == 0

    @pytest.mark.asyncio
    async def test_update(self):
        store = InMemoryProxyStore()
        await store.add(ProxyEntry(address="1.2.3.4:8080", score=1.0))
        await store.update("1.2.3.4:8080", score=0.5)
        entries = await store.get_all()
        assert entries[0].score == 0.5

    @pytest.mark.asyncio
    async def test_count(self):
        store = InMemoryProxyStore()
        assert await store.count() == 0
        await store.add(ProxyEntry(address="1.2.3.4:8080"))
        assert await store.count() == 1

    @pytest.mark.asyncio
    async def test_clear(self):
        store = InMemoryProxyStore()
        await store.add(ProxyEntry(address="1.2.3.4:8080"))
        await store.clear()
        assert await store.count() == 0


class TestProxyPool:
    @pytest.mark.asyncio
    async def test_initialize_with_seeds(self):
        pool = ProxyPool(pool_size=50)
        count = await pool.initialize(seed_proxies=["1.2.3.4:8080", "5.6.7.8:3128"])
        assert count == 2

    @pytest.mark.asyncio
    async def test_acquire_returns_entry(self):
        pool = ProxyPool(pool_size=10)
        await pool.initialize(seed_proxies=["1.2.3.4:8080"])
        entry = await pool.acquire()
        assert entry is not None
        assert "1.2.3.4" in entry.address

    @pytest.mark.asyncio
    async def test_acquire_empty_pool(self):
        pool = ProxyPool(pool_size=10)
        await pool.initialize()
        entry = await pool.acquire()
        assert entry is None

    @pytest.mark.asyncio
    async def test_report_success_increases_score(self):
        pool = ProxyPool(pool_size=10)
        await pool.initialize(seed_proxies=["1.2.3.4:8080"])
        await pool.report("1.2.3.4:8080", success=True, latency=0.3)
        stats = await pool.get_stats()
        assert stats["avg_score"] > 0

    @pytest.mark.asyncio
    async def test_report_failure_decreases_score(self):
        pool = ProxyPool(pool_size=10)
        await pool.initialize(seed_proxies=["1.2.3.4:8080"])
        await pool.report("1.2.3.4:8080", success=False)
        await pool.report("1.2.3.4:8080", success=False)
        await pool.report("1.2.3.4:8080", success=False)
        entry = await pool.acquire()
        assert entry is None  # removed after 3 failures

    @pytest.mark.asyncio
    async def test_add_proxies_respects_pool_size(self):
        pool = ProxyPool(pool_size=2)
        await pool.initialize(seed_proxies=["1.2.3.4:8080"])
        await pool.add_proxies(["5.6.7.8:3128", "9.10.11.12:8080"])
        stats = await pool.get_stats()
        assert stats["total"] <= 2

    @pytest.mark.asyncio
    async def test_get_stats(self):
        pool = ProxyPool(pool_size=10)
        await pool.initialize(seed_proxies=["1.2.3.4:8080", "5.6.7.8:3128"])
        stats = await pool.get_stats()
        assert "total" in stats
        assert "healthy" in stats
        assert "avg_score" in stats

    @pytest.mark.asyncio
    async def test_parse_proxy_with_protocol(self):
        pool = ProxyPool(pool_size=10)
        entry = pool._parse_proxy("socks5://10.0.0.1:1080")
        assert entry is not None
        assert entry.protocol == "socks5"
        assert entry.address == "10.0.0.1:1080"

    @pytest.mark.asyncio
    async def test_parse_proxy_invalid(self):
        pool = ProxyPool(pool_size=10)
        assert pool._parse_proxy("no-port") is None


# ---------------------------------------------------------------------------
# UAPool / Fingerprint tests
# ---------------------------------------------------------------------------


class TestUAPool:
    def test_pool_has_entries(self):
        pool = UAPool(pool_size=50)
        assert pool.size > 0

    def test_random_returns_string(self):
        pool = UAPool(pool_size=50)
        ua = pool.random()
        assert isinstance(ua, str)
        assert "Mozilla" in ua

    def test_next_rotates(self):
        pool = UAPool(pool_size=5)
        uas = [pool.next() for _ in range(pool.size + 2)]
        assert uas[0] == uas[pool.size]  # wraps around

    def test_pool_size_capped(self):
        pool = UAPool(pool_size=10)
        assert pool.size <= 10


class TestFingerprintGenerator:
    def test_generate_returns_profile(self):
        gen = FingerprintGenerator()
        profile = gen.generate()
        assert isinstance(profile, BrowserProfile)
        assert "Mozilla" in profile.user_agent
        assert profile.viewport_width > 0
        assert profile.screen_width >= profile.viewport_width
        assert profile.webgl_vendor
        assert profile.webgl_renderer

    def test_generate_with_custom_ua(self):
        gen = FingerprintGenerator()
        ua = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        profile = gen.generate(ua)
        assert profile.user_agent == ua
        assert profile.platform == "MacIntel"

    def test_generate_headers(self):
        gen = FingerprintGenerator()
        headers = gen.generate_headers()
        assert "User-Agent" in headers
        assert "Accept-Language" in headers
        assert "Accept-Encoding" in headers

    def test_generate_headers_with_profile(self):
        gen = FingerprintGenerator()
        profile = gen.generate()
        headers = gen.generate_headers(profile)
        assert headers["User-Agent"] == profile.user_agent

    def test_linux_platform(self):
        gen = FingerprintGenerator()
        profile = gen.generate("Mozilla/5.0 (X11; Linux x86_64)")
        assert profile.platform == "Linux x86_64"

    def test_canvas_seed_deterministic(self):
        gen = FingerprintGenerator()
        ua = "Mozilla/5.0 test-ua"
        p1 = gen.generate(ua)
        p2 = gen.generate(ua)
        assert p1.canvas_seed == p2.canvas_seed


class TestAntiCrawlProfile:
    def test_next_profile(self):
        ac = AntiCrawlProfile(pool_size=50)
        p1 = ac.next_profile()
        p2 = ac.next_profile()
        assert isinstance(p1, BrowserProfile)
        assert isinstance(p2, BrowserProfile)
        assert p1.user_agent != p2.user_agent  # should rotate

    def test_random_profile(self):
        ac = AntiCrawlProfile(pool_size=50)
        profile = ac.random_profile()
        assert isinstance(profile, BrowserProfile)

    def test_next_headers(self):
        ac = AntiCrawlProfile(pool_size=50)
        headers = ac.next_headers()
        assert "User-Agent" in headers


# ---------------------------------------------------------------------------
# AntiCrawlMiddleware tests
# ---------------------------------------------------------------------------


class TestAntiCrawlMiddleware:
    @pytest.mark.asyncio
    async def test_initialize(self):
        mw = AntiCrawlMiddleware()
        await mw.initialize()
        stats = await mw.get_stats()
        assert stats["initialized"] is True

    @pytest.mark.asyncio
    async def test_before_request_returns_context(self):
        config = AntiCrawlConfig(
            request_delay_min=0,
            request_delay_max=0,
        )
        mw = AntiCrawlMiddleware(config)
        await mw.initialize()
        ctx = await mw.before_request("test_source")
        assert isinstance(ctx, RequestContext)
        assert ctx.source_id == "test_source"
        assert "User-Agent" in ctx.headers

    @pytest.mark.asyncio
    async def test_before_request_without_proxy(self):
        config = AntiCrawlConfig(proxy_rotation=False, request_delay_min=0, request_delay_max=0)
        mw = AntiCrawlMiddleware(config)
        await mw.initialize()
        ctx = await mw.before_request()
        assert ctx.proxy is None

    @pytest.mark.asyncio
    async def test_after_request_success(self):
        mw = AntiCrawlMiddleware(AntiCrawlConfig(request_delay_min=0, request_delay_max=0))
        await mw.initialize(seed_proxies=["1.2.3.4:8080"])
        ctx = await mw.before_request("src")
        await mw.after_request(ctx, success=True)
        stats = await mw.get_stats()
        assert stats["initialized"] is True

    @pytest.mark.asyncio
    async def test_get_stats(self):
        mw = AntiCrawlMiddleware(AntiCrawlConfig(request_delay_min=0, request_delay_max=0))
        await mw.initialize()
        stats = await mw.get_stats()
        assert "ua_pool_size" in stats
        assert "initialized" in stats


# ---------------------------------------------------------------------------
# CrawlerAgent integration with AntiCrawlMiddleware
# ---------------------------------------------------------------------------


class _MockScraper(BaseScraper):
    def __init__(self, docs: list[RawDocument] | None = None):
        self._docs = docs or []

    async def scrape(self, query: str, config=None) -> list[RawDocument]:
        return self._docs


class TestCrawlerWithAntiCrawl:
    @pytest.mark.asyncio
    async def test_crawl_with_middleware(self):
        docs = [RawDocument(
            content="测试文档内容，关于Spring Boot和Docker的微服务架构开发",
            source_type=SourceCategory.NEWS,
            source_name="测试",
        )]
        scraper = _MockScraper(docs)
        config = AntiCrawlConfig(request_delay_min=0, request_delay_max=0)
        mw = AntiCrawlMiddleware(config)

        source = DataSource(
            source_id="test", name="测试源", category=SourceCategory.NEWS,
            priority=5, expected_yield=0.8, rate_limit=10.0,
        )
        crawl_config = CrawlConfig()
        crawl_config.anti_crawl.request_delay_min = 0
        crawl_config.anti_crawl.request_delay_max = 0

        agent = CrawlerAgent(scraper_overrides={"test": scraper}, anti_crawl=mw)
        results = await agent.crawl([source], company_name="XX科技", config=crawl_config)
        assert len(results) == 1
        assert source.status == CollectionStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_crawl_without_middleware(self):
        docs = [RawDocument(
            content="测试文档内容，关于Spring Boot和Docker的微服务架构开发",
            source_type=SourceCategory.NEWS,
            source_name="测试",
        )]
        scraper = _MockScraper(docs)
        source = DataSource(
            source_id="test", name="测试源", category=SourceCategory.NEWS,
            priority=5, expected_yield=0.8, rate_limit=10.0,
        )
        crawl_config = CrawlConfig()
        crawl_config.anti_crawl.request_delay_min = 0
        crawl_config.anti_crawl.request_delay_max = 0

        agent = CrawlerAgent(scraper_overrides={"test": scraper})
        results = await agent.crawl([source], company_name="XX科技", config=crawl_config)
        assert len(results) == 1
