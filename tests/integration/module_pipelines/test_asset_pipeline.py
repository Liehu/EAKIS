"""Integration tests for AssetDiscoveryModule.run() full pipeline."""
from __future__ import annotations

import pytest

from src.asset_discovery.config import AssetDiscoveryConfig
from src.asset_discovery.models import DiscoveryStatus
from src.asset_discovery.module import AssetDiscoveryModule
from src.asset_discovery.services.base import StubSearchClient, StubVectorStore


@pytest.fixture
def module() -> AssetDiscoveryModule:
    return AssetDiscoveryModule(
        config=AssetDiscoveryConfig(),
        search_client=StubSearchClient(),
        vector_store=StubVectorStore(),
    )


@pytest.mark.asyncio
async def test_full_pipeline(module: AssetDiscoveryModule) -> None:
    """Run with DSL queries and verify status + total_searched."""
    result = await module.run(
        task_id="asset-pipe-001",
        dsl_queries=[{"platform": "fofa", "query": "test"}],
    )
    assert result.status == DiscoveryStatus.COMPLETED
    assert result.total_searched > 0


@pytest.mark.asyncio
async def test_pipeline_with_targets(module: AssetDiscoveryModule) -> None:
    """Run with target context; avg_confidence should be > 0."""
    result = await module.run(
        task_id="asset-pipe-002",
        dsl_queries=[{"platform": "fofa", "query": "test"}],
        target_domains=["example.com"],
        target_icp_entity="Example Tech",
        target_ip_ranges=["10.0.0.0/8"],
    )
    assert result.status == DiscoveryStatus.COMPLETED
    assert result.avg_confidence > 0


@pytest.mark.asyncio
async def test_assets_retrievable(module: AssetDiscoveryModule) -> None:
    """get_assets() returns list of dicts with expected keys."""
    await module.run(
        task_id="asset-pipe-003",
        dsl_queries=[{"platform": "fofa", "query": "test"}],
        target_domains=["example.com"],
        target_icp_entity="Example科技有限公司",
    )
    items, total = module.get_assets()
    assert total > 0
    assert len(items) > 0
    for item in items:
        assert "id" in item
        assert "domain" in item
        assert "asset_type" in item
        assert "confidence" in item


@pytest.mark.asyncio
async def test_asset_detail_roundtrip(module: AssetDiscoveryModule) -> None:
    """get_asset(id) returns full detail matching list entry."""
    await module.run(
        task_id="asset-pipe-004",
        dsl_queries=[{"platform": "fofa", "query": "test"}],
        target_domains=["example.com"],
        target_icp_entity="Example科技有限公司",
    )
    items, _ = module.get_assets(page=1, page_size=1)
    assert len(items) > 0, "Expected at least one asset from stub"
    first_id = items[0]["id"]
    detail = module.get_asset(first_id)
    assert detail is not None
    assert detail["id"] == first_id
    assert "domain" in detail
    assert "asset_type" in detail
    assert "confidence" in detail
    assert "risk_level" in detail


@pytest.mark.asyncio
async def test_update_asset(module: AssetDiscoveryModule) -> None:
    """update_asset() changes confirmed and risk_level."""
    await module.run(
        task_id="asset-pipe-005",
        dsl_queries=[{"platform": "fofa", "query": "test"}],
        target_domains=["example.com"],
        target_icp_entity="Example科技有限公司",
    )
    items, _ = module.get_assets(page=1, page_size=1)
    assert len(items) > 0
    updated = module.update_asset(
        items[0]["id"],
        confirmed=True,
        risk_level="high",
    )
    assert updated is not None
    assert updated["confirmed"] is True
    assert updated["risk_level"] == "high"


@pytest.mark.asyncio
async def test_filter_by_risk(module: AssetDiscoveryModule) -> None:
    """get_assets(risk='high') only returns high-risk assets."""
    await module.run(
        task_id="asset-pipe-006",
        dsl_queries=[{"platform": "fofa", "query": "test"}],
    )
    items, _ = module.get_assets(risk="high")
    for item in items:
        assert item["risk_level"] == "high"


@pytest.mark.asyncio
async def test_filter_by_type(module: AssetDiscoveryModule) -> None:
    """get_assets(asset_type='web') only returns web assets."""
    await module.run(
        task_id="asset-pipe-007",
        dsl_queries=[{"platform": "fofa", "query": "test"}],
    )
    items, _ = module.get_assets(asset_type="web")
    for item in items:
        assert item["asset_type"] == "web"


@pytest.mark.asyncio
async def test_pagination(module: AssetDiscoveryModule) -> None:
    """get_assets(page=1, page_size=1) returns paginated result."""
    await module.run(
        task_id="asset-pipe-008",
        dsl_queries=[{"platform": "fofa", "query": "test"}],
    )
    page1, total = module.get_assets(page=1, page_size=1)
    assert isinstance(total, int)
    if total > 0:
        assert len(page1) <= 1


@pytest.mark.asyncio
async def test_empty_queries(module: AssetDiscoveryModule) -> None:
    """Empty DSL queries produce completed status with total_searched=0."""
    result = await module.run(
        task_id="asset-pipe-009",
        dsl_queries=[],
    )
    assert result.status == DiscoveryStatus.COMPLETED
    assert result.total_searched == 0


@pytest.mark.asyncio
async def test_status_matches_result(module: AssetDiscoveryModule) -> None:
    """get_status() returns data consistent with the run result."""
    result = await module.run(
        task_id="asset-pipe-010",
        dsl_queries=[{"platform": "fofa", "query": "test"}],
    )
    status = module.get_status()
    assert status["task_id"] == "asset-pipe-010"
    assert status["status"] == result.status.value
    assert status["total_assets"] == result.total_enriched
