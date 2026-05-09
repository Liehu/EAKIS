"""Unit tests for asset discovery module (orchestration)."""
from __future__ import annotations

import pytest

from src.asset_discovery.config import AssetDiscoveryConfig
from src.asset_discovery.models import DiscoveryStatus, EnrichedAsset, RawAsset
from src.asset_discovery.module import AssetDiscoveryModule
from src.asset_discovery.services.base import StubSearchClient, StubVectorStore


class TestAssetDiscoveryModule:
    @pytest.fixture
    def module(self):
        return AssetDiscoveryModule(
            config=AssetDiscoveryConfig(),
            search_client=StubSearchClient(),
            vector_store=StubVectorStore(),
        )

    @pytest.mark.asyncio
    async def test_run_success(self, module):
        queries = [
            {"platform": "fofa", "query": 'domain="example.com"'},
            {"platform": "hunter", "query": 'web.title="example"'},
        ]
        result = await module.run(
            task_id="test-task-001",
            dsl_queries=queries,
            target_domains=["example.com"],
            target_icp_entity="Example科技有限公司",
        )
        assert result.task_id == "test-task-001"
        assert result.status == DiscoveryStatus.COMPLETED
        assert result.total_searched > 0
        assert result.total_enriched > 0
        assert result.errors == []

    @pytest.mark.asyncio
    async def test_run_with_target_context(self, module):
        result = await module.run(
            task_id="test-task-002",
            dsl_queries=[{"platform": "fofa", "query": "test"}],
            target_domains=["example.com"],
            target_icp_entity="Example Tech",
            target_ip_ranges=["10.0.0.0/8"],
        )
        assert result.status == DiscoveryStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_get_status(self, module):
        await module.run(
            task_id="test-task-003",
            dsl_queries=[{"platform": "fofa", "query": "test"}],
        )
        status = module.get_status()
        assert status["task_id"] == "test-task-003"
        assert status["status"] == "completed"
        assert "total_assets" in status
        assert "by_asset_type" in status

    @pytest.mark.asyncio
    async def test_get_assets_list(self, module):
        await module.run(
            task_id="test-task-004",
            dsl_queries=[{"platform": "fofa", "query": "test"}],
            target_domains=["example.com"],
            target_icp_entity="Example科技有限公司",
        )
        items, total = module.get_assets(page=1, page_size=10)
        assert total > 0
        assert len(items) <= 10
        for item in items:
            assert "id" in item
            assert "domain" in item
            assert "asset_type" in item

    @pytest.mark.asyncio
    async def test_get_assets_filter_by_type(self, module):
        await module.run(
            task_id="test-task-005",
            dsl_queries=[{"platform": "fofa", "query": "test"}],
        )
        items, total = module.get_assets(asset_type="api")
        assert all(i["asset_type"] == "api" for i in items)

    @pytest.mark.asyncio
    async def test_get_assets_filter_by_risk(self, module):
        await module.run(
            task_id="test-task-006",
            dsl_queries=[{"platform": "fofa", "query": "test"}],
        )
        items, total = module.get_assets(risk="high")
        assert all(i["risk_level"] == "high" for i in items)

    @pytest.mark.asyncio
    async def test_get_asset_detail(self, module):
        await module.run(
            task_id="test-task-007",
            dsl_queries=[{"platform": "fofa", "query": "test"}],
        )
        items, _ = module.get_assets(page=1, page_size=1)
        if items:
            detail = module.get_asset(items[0]["id"])
            assert detail is not None
            assert detail["id"] == items[0]["id"]

    @pytest.mark.asyncio
    async def test_get_asset_not_found(self, module):
        result = module.get_asset("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_update_asset(self, module):
        await module.run(
            task_id="test-task-008",
            dsl_queries=[{"platform": "fofa", "query": "test"}],
        )
        items, _ = module.get_assets(page=1, page_size=1)
        if items:
            updated = module.update_asset(
                items[0]["id"],
                confirmed=True,
                risk_level="critical",
                notes="Core gateway",
            )
            assert updated is not None
            assert updated["confirmed"] is True
            assert updated["risk_level"] == "critical"
            assert updated["notes"] == "Core gateway"

    @pytest.mark.asyncio
    async def test_update_nonexistent(self, module):
        result = module.update_asset("nonexistent", confirmed=True)
        assert result is None

    @pytest.mark.asyncio
    async def test_pagination(self, module):
        await module.run(
            task_id="test-task-009",
            dsl_queries=[{"platform": "fofa", "query": "test"}],
        )
        page1, total = module.get_assets(page=1, page_size=1)
        if total > 1:
            page2, _ = module.get_assets(page=2, page_size=1)
            assert len(page1) == 1
            assert page1[0]["id"] != page2[0]["id"]

    @pytest.mark.asyncio
    async def test_empty_queries(self, module):
        result = await module.run(
            task_id="test-task-010",
            dsl_queries=[],
        )
        assert result.status == DiscoveryStatus.COMPLETED
        assert result.total_searched == 0

    @pytest.mark.asyncio
    async def test_vector_store_persist(self):
        module = AssetDiscoveryModule(
            config=AssetDiscoveryConfig(vector_store_enabled=True),
            search_client=StubSearchClient(),
            vector_store=StubVectorStore(),
        )
        result = await module.run(
            task_id="test-task-011",
            dsl_queries=[{"platform": "fofa", "query": "test"}],
        )
        assert result.status == DiscoveryStatus.COMPLETED
