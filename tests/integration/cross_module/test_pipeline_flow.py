"""Cross-module integration tests for the M1 -> M3 -> M4 pipeline.

Verifies that data flows correctly between:
  M1  IntelligenceModule   (keyword extraction / DSL generation)
  M3  AssetDiscoveryModule (asset search from DSL queries)
  M4  ApiCrawlerModule     (interface classification from assets)

All modules run in stub mode -- no external services required.
"""

from __future__ import annotations

import pytest
from uuid import uuid4

from src.api_crawler.module import ApiCrawlerModule
from src.asset_discovery.module import AssetDiscoveryModule
from src.intelligence.config import IntelligenceConfig
from src.intelligence.module import IntelligenceModule


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _task_id() -> str:
    return f"test-{uuid4().hex[:8]}"


# ---------------------------------------------------------------------------
# Test 1: Intelligence feeds AssetDiscovery
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_intelligence_feeds_asset_discovery() -> None:
    """M1 DSL queries are valid input for M3 AssetDiscoveryModule.run()."""
    intel = IntelligenceModule(config=IntelligenceConfig())

    task = _task_id()
    result = await intel.run(
        task_id=task,
        company_name="Example Corp",
        industry="fintech",
        keywords=["支付系统", "API网关"],
    )
    assert result.status in ("completed", "partial_failure"), (
        f"Intelligence run failed: {result.errors}"
    )

    dsl_queries = intel.get_dsl_queries()
    assert len(dsl_queries) > 0, "Expected at least one DSL query from intelligence"

    # Each DSL dict must have the keys AssetDiscovery expects.
    for q in dsl_queries:
        assert "platform" in q, "DSL query missing 'platform' key"
        assert "query" in q, "DSL query missing 'query' key"

    discovery = AssetDiscoveryModule()
    disc_result = await discovery.run(
        task_id=_task_id(),
        dsl_queries=dsl_queries,
    )
    assert disc_result.total_searched > 0, (
        "Asset discovery should find candidates from intelligence DSL queries"
    )


# ---------------------------------------------------------------------------
# Test 2: AssetDiscovery feeds ApiCrawler
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_asset_feeds_interface_crawler() -> None:
    """M3 assets are valid input for M4 ApiCrawlerModule.run()."""
    discovery = AssetDiscoveryModule()

    mock_queries = [
        {"platform": "fofa", "query": 'domain="example.com"'},
        {"platform": "hunter", "query": 'domain.suffix="example.com"'},
    ]
    disc_result = await discovery.run(
        task_id=_task_id(),
        dsl_queries=mock_queries,
        target_domains=["example.com"],
    )
    assert disc_result.status in ("completed", "partial_failure"), (
        f"Asset discovery failed: {disc_result.errors}"
    )

    assets, total = discovery.get_assets(page_size=50)
    assert total > 0, "Expected at least one asset from discovery"

    # Build the asset list the crawler expects (needs 'url' and 'asset_id').
    crawler_assets: list[dict] = []
    for a in assets:
        domain = a.get("domain") or "unknown.example.com"
        scheme = "https" if a.get("port") == 443 else "http"
        crawler_assets.append({
            "asset_id": a["id"],
            "url": f"{scheme}://{domain}",
        })

    crawler = ApiCrawlerModule()
    crawl_result = await crawler.run(
        task_id=_task_id(),
        assets=crawler_assets,
    )
    assert crawl_result.total_classified > 0, (
        "Crawler should classify interfaces from asset URLs"
    )


# ---------------------------------------------------------------------------
# Test 3: Intelligence document structure
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_intelligence_to_keywords_data_flow() -> None:
    """Documents produced by M1 have the structure the keyword engine expects."""
    intel = IntelligenceModule(config=IntelligenceConfig())

    await intel.run(
        task_id=_task_id(),
        company_name="Example Corp",
        industry="fintech",
        keywords=["支付系统"],
    )

    documents = intel.get_documents()
    assert len(documents) > 0, "Expected at least one cleaned document"

    required_keys = {"content", "quality_score", "source_name"}
    for doc in documents:
        missing = required_keys - doc.keys()
        assert not missing, f"Document missing keys: {missing}"

        assert isinstance(doc["content"], str) and len(doc["content"]) > 0, (
            "Document 'content' must be a non-empty string"
        )
        assert isinstance(doc["quality_score"], float), (
            "Document 'quality_score' must be a float"
        )
        assert 0.0 <= doc["quality_score"] <= 1.0, (
            "quality_score must be between 0.0 and 1.0"
        )


# ---------------------------------------------------------------------------
# Test 4: Full pipeline M1 -> M3 -> M4
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_full_m1_to_m4_pipeline() -> None:
    """End-to-end data flow through all three module stages."""

    # -- Stage 1: Intelligence (M1) --
    intel = IntelligenceModule(config=IntelligenceConfig())
    m1_task = _task_id()
    m1_result = await intel.run(
        task_id=m1_task,
        company_name="Example Corp",
        industry="ecommerce",
        domains=["example.com"],
        keywords=["支付", "订单管理"],
    )
    assert m1_result.status in ("completed", "partial_failure"), (
        f"M1 stage failed: {m1_result.errors}"
    )
    assert m1_result.cleaned_documents > 0, "M1 should produce cleaned documents"

    dsl_queries = intel.get_dsl_queries()
    assert len(dsl_queries) > 0, "M1 should produce DSL queries for downstream"

    # -- Stage 2: AssetDiscovery (M3) --
    discovery = AssetDiscoveryModule()
    m3_task = _task_id()
    m3_result = await discovery.run(
        task_id=m3_task,
        dsl_queries=dsl_queries,
        target_domains=["example.com"],
    )
    assert m3_result.status in ("completed", "partial_failure"), (
        f"M3 stage failed: {m3_result.errors}"
    )
    assert m3_result.total_searched > 0, "M3 should search assets from DSL"

    assets, total = discovery.get_assets(page_size=50)
    assert total > 0, "M3 should produce enriched assets"

    # -- Stage 3: ApiCrawler (M4) --
    crawler_assets: list[dict] = []
    for a in assets:
        domain = a.get("domain") or "unknown.example.com"
        scheme = "https" if a.get("port") == 443 else "http"
        crawler_assets.append({
            "asset_id": a["id"],
            "url": f"{scheme}://{domain}",
        })

    crawler = ApiCrawlerModule()
    m4_task = _task_id()
    m4_result = await crawler.run(
        task_id=m4_task,
        assets=crawler_assets,
    )
    assert m4_result.status in ("completed",), (
        f"M4 stage failed: {m4_result.errors}"
    )
    assert m4_result.total_classified > 0, "M4 should classify interfaces"
    assert m4_result.total_assets == len(crawler_assets), (
        "M4 should process every input asset"
    )


# ---------------------------------------------------------------------------
# Test 5: Error does not cascade downstream
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_error_doesnt_cascade() -> None:
    """Graceful degradation: empty input does not crash downstream modules."""
    intel = IntelligenceModule(config=IntelligenceConfig())

    m1_result = await intel.run(
        task_id=_task_id(),
        company_name="Empty Corp",
        # No industry, no keywords -- minimal input
    )
    # M1 must return a valid CollectionResult even with no keywords.
    assert m1_result.task_id, "Result must have a task_id"
    assert m1_result.status in ("completed", "partial_failure", "failed"), (
        "Result must have a valid status"
    )

    # Downstream M3 should still accept an empty DSL list.
    discovery = AssetDiscoveryModule()
    empty_dsl: list[dict[str, str]] = intel.get_dsl_queries()
    m3_result = await discovery.run(
        task_id=_task_id(),
        dsl_queries=empty_dsl,
    )
    assert m3_result.status in ("completed", "failed"), (
        "M3 must not raise on empty DSL input"
    )


# ---------------------------------------------------------------------------
# Test 6: Modules use stub mode by default
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_modules_use_stub_mode() -> None:
    """Default construction uses stub implementations -- no external I/O."""
    intel = IntelligenceModule()
    assert intel.config.use_stubs is True, (
        "IntelligenceConfig.use_stubs should default to True"
    )
    # The stub RAG client is a StubRAGClient (no Qdrant connection).
    from src.intelligence.services.rag_client import StubRAGClient
    assert isinstance(intel.rag_client, StubRAGClient), (
        "Default RAG client must be StubRAGClient"
    )

    discovery = AssetDiscoveryModule()
    assert discovery.config.use_stubs is True, (
        "AssetDiscoveryConfig.use_stubs should default to True"
    )
    from src.asset_discovery.services.base import StubSearchClient, StubVectorStore
    assert isinstance(discovery.search_client, StubSearchClient), (
        "Default search client must be StubSearchClient"
    )
    assert isinstance(discovery.vector_store, StubVectorStore), (
        "Default vector store must be StubVectorStore"
    )

    crawler = ApiCrawlerModule()
    assert crawler.config.use_stubs is True, (
        "CrawlerConfig.use_stubs should default to True"
    )

    # Smoke-test: run each module to confirm no external connections.
    intel_result = await intel.run(
        task_id=_task_id(),
        company_name="Stub Corp",
        keywords=["test"],
    )
    assert intel_result.errors == [], (
        f"Stub intelligence should not produce errors: {intel_result.errors}"
    )

    disc_result = await discovery.run(
        task_id=_task_id(),
        dsl_queries=[{"platform": "fofa", "query": 'domain="stub.com"'}],
    )
    assert disc_result.errors == [], (
        f"Stub discovery should not produce errors: {disc_result.errors}"
    )

    crawl_result = await crawler.run(
        task_id=_task_id(),
        assets=[{"asset_id": "stub-1", "url": "https://stub.example.com"}],
    )
    assert crawl_result.errors == [], (
        f"Stub crawler should not produce errors: {crawl_result.errors}"
    )
