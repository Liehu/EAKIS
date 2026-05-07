from __future__ import annotations

import pytest

from src.api_crawler.config import CrawlerConfig
from src.api_crawler.models import CrawlStatus
from src.api_crawler.module import ApiCrawlerModule


@pytest.fixture
def module() -> ApiCrawlerModule:
    return ApiCrawlerModule(config=CrawlerConfig())


class TestRun:
    @pytest.mark.asyncio
    async def test_crawl_with_assets_returns_result(self, module: ApiCrawlerModule):
        assets = [
            {"asset_id": "a1", "url": "https://example.com", "domain": "example.com"},
        ]
        result = await module.run(task_id="t1", assets=assets)
        assert result.status == CrawlStatus.COMPLETED
        assert result.total_assets == 1
        assert result.total_classified > 0

    @pytest.mark.asyncio
    async def test_crawl_with_empty_assets(self, module: ApiCrawlerModule):
        result = await module.run(task_id="t2", assets=[])
        assert result.status == CrawlStatus.COMPLETED
        assert result.total_assets == 0

    @pytest.mark.asyncio
    async def test_crawl_result_has_type_summary(self, module: ApiCrawlerModule):
        assets = [{"asset_id": "a1", "url": "https://example.com"}]
        result = await module.run(task_id="t3", assets=assets)
        assert isinstance(result.by_type, dict)

    @pytest.mark.asyncio
    async def test_multiple_assets(self, module: ApiCrawlerModule):
        assets = [
            {"asset_id": "a1", "url": "https://example.com"},
            {"asset_id": "a2", "url": "https://other.com"},
        ]
        result = await module.run(task_id="t4", assets=assets)
        assert result.total_assets == 2


class TestGetInterfaces:
    @pytest.mark.asyncio
    async def test_get_interfaces_returns_list(self, module: ApiCrawlerModule):
        assets = [{"asset_id": "a1", "url": "https://example.com"}]
        await module.run(task_id="t5", assets=assets)
        interfaces = module.get_interfaces()
        assert isinstance(interfaces, list)
        assert len(interfaces) > 0

    @pytest.mark.asyncio
    async def test_filter_by_asset_id(self, module: ApiCrawlerModule):
        assets = [
            {"asset_id": "a1", "url": "https://example.com"},
            {"asset_id": "a2", "url": "https://other.com"},
        ]
        await module.run(task_id="t6", assets=assets)
        filtered = module.get_interfaces(asset_id="a1")
        assert all(i["asset_id"] == "a1" for i in filtered)

    @pytest.mark.asyncio
    async def test_filter_by_type(self, module: ApiCrawlerModule):
        assets = [{"asset_id": "a1", "url": "https://example.com"}]
        await module.run(task_id="t7", assets=assets)
        filtered = module.get_interfaces(api_type="query")
        assert all(i["api_type"] == "query" for i in filtered)

    @pytest.mark.asyncio
    async def test_get_single_interface(self, module: ApiCrawlerModule):
        assets = [{"asset_id": "a1", "url": "https://example.com"}]
        await module.run(task_id="t8", assets=assets)
        interfaces = module.get_interfaces()
        iface_id = interfaces[0]["interface_id"]
        result = module.get_interface(iface_id)
        assert result is not None
        assert result["interface_id"] == iface_id

    @pytest.mark.asyncio
    async def test_update_interface(self, module: ApiCrawlerModule):
        assets = [{"asset_id": "a1", "url": "https://example.com"}]
        await module.run(task_id="t9", assets=assets)
        interfaces = module.get_interfaces()
        iface_id = interfaces[0]["interface_id"]
        module.update_interface(iface_id, test_priority=10, notes="high risk")
        updated = module.get_interface(iface_id)
        assert updated["test_priority"] == 10
        assert updated["notes"] == "high risk"

    @pytest.mark.asyncio
    async def test_get_nonexistent_interface(self, module: ApiCrawlerModule):
        result = module.get_interface("nonexistent-id")
        assert result is None


class TestGetStatus:
    @pytest.mark.asyncio
    async def test_status_after_run(self, module: ApiCrawlerModule):
        assets = [{"asset_id": "a1", "url": "https://example.com"}]
        await module.run(task_id="t10", assets=assets)
        status = module.get_status()
        assert status["status"] == CrawlStatus.COMPLETED.value
        assert "total_interfaces" in status
