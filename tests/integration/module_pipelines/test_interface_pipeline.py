"""Integration tests for ApiCrawlerModule.run() full pipeline."""
from __future__ import annotations

import pytest

from src.api_crawler.config import CrawlerConfig
from src.api_crawler.models import CrawlStatus
from src.api_crawler.module import ApiCrawlerModule


@pytest.fixture
def module() -> ApiCrawlerModule:
    return ApiCrawlerModule(config=CrawlerConfig())


SAMPLE_ASSETS = [
    {"asset_id": "a1", "url": "https://example.com"},
    {"asset_id": "a2", "url": "https://other.com"},
    {"asset_id": "a3", "url": "https://third.com"},
]


@pytest.mark.asyncio
async def test_full_pipeline(module: ApiCrawlerModule) -> None:
    """Run with one asset; verify status, asset count, and classified > 0."""
    result = await module.run(
        task_id="iface-pipe-001",
        assets=[SAMPLE_ASSETS[0]],
    )
    assert result.status == CrawlStatus.COMPLETED
    assert result.total_assets == 1
    assert result.total_classified > 0


@pytest.mark.asyncio
async def test_multiple_assets(module: ApiCrawlerModule) -> None:
    """Run with 3 assets; total_assets must be 3."""
    result = await module.run(
        task_id="iface-pipe-002",
        assets=SAMPLE_ASSETS,
    )
    assert result.status == CrawlStatus.COMPLETED
    assert result.total_assets == 3


@pytest.mark.asyncio
async def test_interfaces_retrievable(module: ApiCrawlerModule) -> None:
    """get_interfaces() returns dicts with expected keys."""
    await module.run(
        task_id="iface-pipe-003",
        assets=[SAMPLE_ASSETS[0]],
    )
    interfaces = module.get_interfaces()
    assert len(interfaces) > 0
    for iface in interfaces:
        assert "interface_id" in iface
        assert "asset_id" in iface
        assert "path" in iface
        assert "method" in iface
        assert "api_type" in iface


@pytest.mark.asyncio
async def test_filter_by_asset_id(module: ApiCrawlerModule) -> None:
    """Filtering by asset_id returns only interfaces for that asset."""
    await module.run(
        task_id="iface-pipe-004",
        assets=[SAMPLE_ASSETS[0], SAMPLE_ASSETS[1]],
    )
    filtered = module.get_interfaces(asset_id="a1")
    for iface in filtered:
        assert iface["asset_id"] == "a1"


@pytest.mark.asyncio
async def test_filter_by_method(module: ApiCrawlerModule) -> None:
    """Filtering by method returns only matching HTTP methods."""
    await module.run(
        task_id="iface-pipe-005",
        assets=[SAMPLE_ASSETS[0]],
    )
    filtered = module.get_interfaces(method="GET")
    for iface in filtered:
        assert iface["method"] == "GET"


@pytest.mark.asyncio
async def test_interface_detail(module: ApiCrawlerModule) -> None:
    """get_interface() returns full detail dict with all expected fields."""
    await module.run(
        task_id="iface-pipe-006",
        assets=[SAMPLE_ASSETS[0]],
    )
    interfaces = module.get_interfaces()
    assert len(interfaces) > 0
    iface_id = interfaces[0]["interface_id"]
    detail = module.get_interface(iface_id)
    assert detail is not None
    assert detail["interface_id"] == iface_id
    assert "path" in detail
    assert "method" in detail
    assert "api_type" in detail
    assert "parameters" in detail
    assert "test_priority" in detail
    assert "skip_test" in detail
    assert "notes" in detail


@pytest.mark.asyncio
async def test_update_interface(module: ApiCrawlerModule) -> None:
    """update_interface() changes test_priority and notes."""
    await module.run(
        task_id="iface-pipe-007",
        assets=[SAMPLE_ASSETS[0]],
    )
    interfaces = module.get_interfaces()
    assert len(interfaces) > 0
    iface_id = interfaces[0]["interface_id"]
    updated = module.update_interface(iface_id, test_priority=10, notes="test")
    assert updated is not None
    assert updated["test_priority"] == 10
    assert updated["notes"] == "test"


@pytest.mark.asyncio
async def test_pipeline_status(module: ApiCrawlerModule) -> None:
    """get_status() returns dict with expected keys after pipeline."""
    await module.run(
        task_id="iface-pipe-008",
        assets=[SAMPLE_ASSETS[0]],
    )
    status = module.get_status()
    assert status["status"] == CrawlStatus.COMPLETED.value
    assert "total_interfaces" in status
    assert "by_type" in status
    assert "privilege_sensitive_count" in status


@pytest.mark.asyncio
async def test_empty_assets(module: ApiCrawlerModule) -> None:
    """Empty assets list produces completed status with total_assets=0."""
    result = await module.run(
        task_id="iface-pipe-009",
        assets=[],
    )
    assert result.status == CrawlStatus.COMPLETED
    assert result.total_assets == 0


@pytest.mark.asyncio
async def test_privilege_sensitive_count(module: ApiCrawlerModule) -> None:
    """Result contains privilege_sensitive_count >= 0."""
    result = await module.run(
        task_id="iface-pipe-010",
        assets=[SAMPLE_ASSETS[0]],
    )
    assert result.privilege_sensitive_count >= 0
