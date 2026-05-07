import pytest

from src.intelligence.agents.cleaner import CleanerAgent
from src.intelligence.agents.crawler import CrawlerAgent
from src.intelligence.agents.datasource import DataSourceAgent
from src.intelligence.agents.dsl import DSLAgent
from src.intelligence.config import CrawlConfig
from src.intelligence.engine_specs import build_all_field_docs, load_engine_specs
from src.intelligence.models import (
    CleanedDocument,
    CollectionStatus,
    DataSource,
    DslQuery,
    RawDocument,
    SourceCategory,
)
from src.intelligence.services.base import BaseLLMClient, BaseRAGClient, BaseScraper
from src.intelligence.services.generic_scraper import GenericEngineScraper


# --- Stub implementations for testing ---

class MockRAGClient(BaseRAGClient):
    def __init__(self):
        self.upserted: list[list[CleanedDocument]] = []

    async def upsert(self, docs: list[CleanedDocument], task_id: str) -> int:
        self.upserted.append(docs)
        return len(docs)

    async def search(self, query: str, top_k: int = 10, filter=None):
        return []


class MockLLMClient(BaseLLMClient):
    async def generate(self, prompt: str, **kwargs) -> str:
        return '{"fofa": "domain=\\"test.com\\"", "hunter": "domain.suffix=\\"test.com\\"", "shodan": "org:\\"Test Corp\\""}'


class MockScraper(BaseScraper):
    def __init__(self, docs: list[RawDocument] | None = None):
        self._docs = docs or []

    async def scrape(self, query: str, config=None) -> list[RawDocument]:
        return self._docs


def _make_raw_doc(content: str = "这是一段较长的测试文本内容，XX科技使用Spring Boot和Docker进行微服务架构开发，该技术方案已在多个大型金融项目中成功落地并稳定运行超过两年时间") -> RawDocument:
    from datetime import datetime, timezone
    return RawDocument(
        content=content,
        source_type=SourceCategory.NEWS,
        source_name="测试来源",
        source_url="https://example.com/test",
        published_at=datetime.now(timezone.utc),
    )


# --- Engine specs tests ---

def test_load_engine_specs():
    specs = load_engine_specs()
    assert "fofa" in specs
    assert "hunter" in specs
    assert "shodan" in specs
    assert len(specs) >= 3


def test_engine_spec_has_required_fields():
    specs = load_engine_specs()
    for name, spec in specs.items():
        assert spec.display_name, f"{name} missing display_name"
        assert spec.search_url, f"{name} missing search_url"
        assert spec.fields, f"{name} missing fields"
        assert spec.operators, f"{name} missing operators"


def test_build_field_docs():
    docs = build_all_field_docs(["fofa", "hunter"])
    assert "Fofa" in docs
    assert "Hunter" in docs
    assert "domain=" in docs


def test_build_all_field_docs_with_no_filter():
    docs = build_all_field_docs()
    assert "Fofa" in docs
    assert "Shodan" in docs


# --- DataSourceAgent tests ---

@pytest.mark.asyncio
async def test_datasource_agent_returns_sources():
    agent = DataSourceAgent(MockRAGClient())
    sources = await agent.select_sources("XX科技", "fintech")
    assert len(sources) > 0
    assert all(isinstance(s, DataSource) for s in sources)


@pytest.mark.asyncio
async def test_datasource_agent_filters_by_category():
    agent = DataSourceAgent(MockRAGClient())
    sources = await agent.select_sources("XX科技", enabled_categories=[SourceCategory.NEWS])
    assert all(s.category == SourceCategory.NEWS for s in sources)


@pytest.mark.asyncio
async def test_datasource_agent_sorts_by_priority():
    agent = DataSourceAgent(MockRAGClient())
    sources = await agent.select_sources("XX科技")
    priorities = [s.priority for s in sources]
    assert priorities == sorted(priorities, reverse=True)


@pytest.mark.asyncio
async def test_datasource_agent_includes_all_engines():
    agent = DataSourceAgent(MockRAGClient())
    sources = await agent.select_sources("XX科技", enabled_categories=[SourceCategory.ASSET_ENGINE])
    source_ids = {s.source_id for s in sources}
    specs = load_engine_specs()
    for engine_name in specs:
        assert engine_name in source_ids, f"引擎 {engine_name} 未出现在数据源中"


# --- DSLAgent tests ---

@pytest.mark.asyncio
async def test_dsl_agent_generates_via_llm():
    agent = DSLAgent(MockLLMClient())
    queries = await agent.generate(["XX科技"], domains=["xx-tech.com"])
    assert len(queries) > 0
    assert all(isinstance(q, DslQuery) for q in queries)


@pytest.mark.asyncio
async def test_dsl_agent_template_fallback():
    class FailLLM(BaseLLMClient):
        async def generate(self, prompt: str, **kwargs) -> str:
            raise RuntimeError("LLM unavailable")

    agent = DSLAgent(FailLLM())
    queries = await agent.generate(["XX科技"], domains=["xx-tech.com"])
    assert len(queries) > 0
    assert all(q.syntax_valid for q in queries)


@pytest.mark.asyncio
async def test_dsl_agent_uses_engine_specs():
    agent = DSLAgent(MockLLMClient())
    queries = await agent.generate(["XX科技"], domains=["xx-tech.com"])
    platforms = {q.platform for q in queries}
    assert len(platforms) >= 1


@pytest.mark.asyncio
async def test_dsl_agent_unknown_platform_skipped():
    agent = DSLAgent(MockLLMClient())
    queries = await agent.generate(["XX科技"], platforms=["nonexistent"])
    assert len(queries) == 0


# --- GenericEngineScraper tests ---

@pytest.mark.asyncio
async def test_generic_scraper_returns_docs():
    scraper = GenericEngineScraper("fofa")
    docs = await scraper.scrape("test query")
    assert len(docs) > 0
    assert all(d.source_type == SourceCategory.ASSET_ENGINE for d in docs)


@pytest.mark.asyncio
async def test_generic_scraper_unknown_engine():
    scraper = GenericEngineScraper("unknown_engine")
    docs = await scraper.scrape("test query")
    assert len(docs) > 0  # stub still returns data


# --- query_encoding tests ---

def test_encode_query_base64():
    from src.intelligence.engine_specs import encode_query
    encoded = encode_query('domain="example.com"', "base64")
    import base64
    assert encoded == base64.b64encode(b'domain="example.com"').decode("ascii")


def test_encode_query_url():
    from src.intelligence.engine_specs import encode_query
    encoded = encode_query('domain="test&val"', "url")
    assert "%26" in encoded


def test_encode_query_none():
    from src.intelligence.engine_specs import encode_query
    assert encode_query("domain=example", "none") == "domain=example"


@pytest.mark.asyncio
async def test_generic_scraper_fofa_builds_base64_url():
    scraper = GenericEngineScraper("fofa")
    docs = await scraper.scrape('domain="test.com"')
    url = docs[0].source_url
    assert "fofa.info" in url
    assert "qbase64=" in url


@pytest.mark.asyncio
async def test_generic_scraper_hunter_builds_plain_url():
    scraper = GenericEngineScraper("hunter")
    docs = await scraper.scrape('domain.suffix="test.com"')
    url = docs[0].source_url
    assert "hunter.qianxin.com" in url
    assert "query=" in url


def test_engine_specs_have_query_fields():
    specs = load_engine_specs()
    for name, spec in specs.items():
        assert spec.query_param, f"{name} missing query_param"
        assert spec.query_encoding in ("none", "base64", "url"), f"{name} invalid query_encoding: {spec.query_encoding}"


# --- CrawlerAgent tests ---

@pytest.mark.asyncio
async def test_crawler_agent_crawls_sources():
    docs = [_make_raw_doc(), _make_raw_doc("第二篇关于Kubernetes微服务容器化部署的技术实践文档，详细介绍了从传统架构迁移到云原生架构的完整过程")]
    scraper = MockScraper(docs)
    source = DataSource(
        source_id="test", name="测试源", category=SourceCategory.NEWS,
        priority=5, expected_yield=0.8, rate_limit=10.0,
    )
    agent = CrawlerAgent(scraper_overrides={"test": scraper})
    config = CrawlConfig()
    config.anti_crawl.request_delay_min = 0
    config.anti_crawl.request_delay_max = 0
    results = await agent.crawl([source], company_name="XX科技", config=config)
    assert len(results) == 2


@pytest.mark.asyncio
async def test_crawler_agent_handles_single_failure():
    class FailScraper(BaseScraper):
        async def scrape(self, query: str, config=None) -> list[RawDocument]:
            raise RuntimeError("connection refused")

    ok_scraper = MockScraper([_make_raw_doc()])
    fail_scraper = FailScraper()

    sources = [
        DataSource(source_id="ok", name="OK源", category=SourceCategory.NEWS, priority=5, expected_yield=0.8, rate_limit=10),
        DataSource(source_id="fail", name="失败源", category=SourceCategory.NEWS, priority=3, expected_yield=0.5, rate_limit=10),
    ]
    agent = CrawlerAgent(scraper_overrides={"ok": ok_scraper, "fail": fail_scraper})
    config = CrawlConfig()
    config.anti_crawl.request_delay_min = 0
    config.anti_crawl.request_delay_max = 0
    results = await agent.crawl(sources, company_name="XX科技", config=config)
    assert len(results) == 1


# --- CleanerAgent tests ---

@pytest.mark.asyncio
async def test_cleaner_agent_cleans_documents():
    rag = MockRAGClient()
    agent = CleanerAgent(rag)
    docs = [_make_raw_doc(), _make_raw_doc("第二篇关于Kubernetes和微服务的技术文档")]
    cleaned = await agent.clean(docs, "task-123")
    assert len(cleaned) >= 1
    assert all(d.quality_score > 0 for d in cleaned)
    assert len(rag.upserted) == 1


@pytest.mark.asyncio
async def test_cleaner_agent_deduplicates():
    rag = MockRAGClient()
    agent = CleanerAgent(rag)
    doc = _make_raw_doc("重复内容测试文本，包含Docker和Kubernetes技术栈的详细技术方案介绍文档，该方案已在生产环境稳定运行")
    cleaned = await agent.clean([doc, doc], "task-123")
    assert len(cleaned) == 1


@pytest.mark.asyncio
async def test_cleaner_agent_filters_short_text():
    rag = MockRAGClient()
    agent = CleanerAgent(rag)
    docs = [RawDocument(content="短", source_type=SourceCategory.NEWS, source_name="test")]
    cleaned = await agent.clean(docs, "task-123")
    assert len(cleaned) == 0


@pytest.mark.asyncio
async def test_cleaner_agent_extracts_entities():
    rag = MockRAGClient()
    agent = CleanerAgent(rag)
    doc = _make_raw_doc("XX科技使用Spring Boot和Docker进行微服务架构开发，并采用Kubernetes进行容器编排管理，系统已上线运行")
    cleaned = await agent.clean([doc], "task-123")
    assert len(cleaned) == 1
    entities = cleaned[0].entities
    assert any("Spring Boot" in e for e in entities)
    assert any("Docker" in e for e in entities)
