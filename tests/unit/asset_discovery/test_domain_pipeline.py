"""Unit tests for the real-tool domain pipeline (subfinder→dnsx→httpx→naabu)
and the RawAsset→Asset idempotent persistence."""
from __future__ import annotations

import pytest
import pytest_asyncio

from src.asset_discovery.models import RawAsset
from src.asset_discovery.services.domain_pipeline import run_domain_pipeline
from src.asset_discovery.services.persistence import upsert_assets
from src.models.asset import Asset
from src.models.company import Company
from src.models.task import Task


class FakeChainClient:
    """按平台返回构造好的 RawAsset，模拟真实工具链输出。"""

    async def search(self, platform: str, query: str, page_size: int = 100, max_pages: int = 10):
        q = query.strip().lower()
        if platform == "subfinder":
            if q == "example.com":
                return [
                    RawAsset(domain="www.example.com", source_platform="subfinder"),
                    RawAsset(domain="api.example.com", source_platform="subfinder"),
                ]
            return []
        if platform == "cert":
            return [RawAsset(domain="dev.example.com", source_platform="cert")] if q == "example.com" else []
        if platform == "dnsx":
            if q in ("www.example.com", "api.example.com", "dev.example.com", "example.com"):
                return [RawAsset(domain=q, ip_address="1.2.3.4", source_platform="dnsx")]
            return []
        if platform == "httpx":
            if q == "www.example.com":
                return [RawAsset(
                    domain="www.example.com", ip_address="1.2.3.4", port=443,
                    title="Example Site", source_platform="httpx",
                    metadata={"tech": ["nginx"]},
                )]
            return []
        if platform == "naabu":
            if q == "1.2.3.4":
                return [
                    RawAsset(domain=None, ip_address="1.2.3.4", port=443, source_platform="naabu"),
                    RawAsset(domain=None, ip_address="1.2.3.4", port=22, protocol="tcp", source_platform="naabu"),
                ]
            return []
        return []


class EmptyClient:
    """所有工具不可用（降级路径）。"""

    async def search(self, platform, query, page_size=100, max_pages=10):
        return []


@pytest.mark.asyncio
async def test_domain_pipeline_full_chain():
    assets, errors = await run_domain_pipeline(FakeChainClient(), ["example.com"])
    by_domain = {a["domain"]: a for a in assets if a["domain"]}
    # 子域枚举：subfinder + cert 都生效
    assert {"www.example.com", "api.example.com", "dev.example.com"} <= set(by_domain)
    # httpx 存活资产带端口/技术栈
    www = by_domain["www.example.com"]
    assert www["ip_address"] == "1.2.3.4"
    assert 443 in www["open_ports"]
    assert "nginx" in www["tech_stack"]
    assert www["confirmed"] is True
    # naabu 端口回填：22 端口并入同一资产
    assert 22 in www["open_ports"]


@pytest.mark.asyncio
async def test_domain_pipeline_degrades_gracefully():
    assets, errors = await run_domain_pipeline(EmptyClient(), ["example.com"])
    assert assets == []
    assert errors  # 降级信息被记录而不是抛异常


@pytest.mark.asyncio
async def test_domain_pipeline_no_seeds():
    assets, errors = await run_domain_pipeline(FakeChainClient(), [])
    assert assets == []
    assert any("种子域名" in e for e in errors)


@pytest_asyncio.fixture
async def task_and_company(async_session):
    import uuid

    from src.models.organization import Organization  # noqa: F401  (org_id 外键)

    org_id = uuid.uuid4()
    async_session.add(Organization(id=org_id, name="测试组织", slug=f"test-org-{org_id.hex[:8]}"))
    await async_session.flush()
    company = Company(org_id=org_id, name="示例公司", domains=["example.com"])
    async_session.add(company)
    await async_session.flush()
    task = Task(
        company_id=company.id, company_name=company.name,
        status="running", config={"modules": ["M3"]},
        authorized_scope={"domains": ["example.com"]},
    )
    async_session.add(task)
    await async_session.commit()
    return task, company


@pytest.mark.asyncio
async def test_upsert_assets_idempotent(async_session, task_and_company):
    task, company = task_and_company
    assets, _ = await run_domain_pipeline(FakeChainClient(), ["example.com"])

    stats1 = await upsert_assets(async_session, task, assets, company=company)
    assert stats1["inserted"] > 0

    rows = (await async_session.execute(
        __import__("sqlalchemy").select(Asset).where(Asset.task_id == task.id)
    )).scalars().all()
    first_count = len(rows)
    www = next(r for r in rows if r.domain == "www.example.com")
    assert www.ip_address == "1.2.3.4"
    assert 22 in (www.open_ports or [])
    assert www.company_id == company.id

    # 重跑同一批：全部走更新，不产生重复行
    stats2 = await upsert_assets(async_session, task, assets, company=company)
    assert stats2["inserted"] == 0
    rows2 = (await async_session.execute(
        __import__("sqlalchemy").select(Asset).where(Asset.task_id == task.id)
    )).scalars().all()
    assert len(rows2) == first_count
    # 多来源融合：置信度提升但封顶 1.0
    www2 = next(r for r in rows2 if r.domain == "www.example.com")
    assert www2.confidence_score <= 1.0
    assert www2.miss_count == 0
    assert www2.last_seen_at is not None
