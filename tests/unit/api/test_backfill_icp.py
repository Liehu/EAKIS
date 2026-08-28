"""ICP 回填测试：query_icp 结果 → Company.icp_* / Asset.icp_* / IntelDocument。"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import select

from src.api.services.task_runner import _backfill_icp
from src.intelligence.scrapers import icp_scraper
from src.models.asset import Asset
from src.models.company import Company
from src.models.intel_document import IntelDocument
from src.models.organization import Organization
from src.models.task import Task


@pytest.fixture
async def task_company_assets(async_session):
    org_id = uuid.uuid4()
    async_session.add(Organization(id=org_id, name="测试组织", slug=f"t-{org_id.hex[:8]}"))
    await async_session.flush()
    company = Company(org_id=org_id, name="示例科技", domains=["example.com"])
    async_session.add(company)
    await async_session.flush()
    task = Task(
        company_id=company.id, company_name=company.name, status="running",
        config={"modules": ["M1"]}, authorized_scope={"domains": ["example.com"]},
    )
    async_session.add(task)
    await async_session.flush()
    async_session.add(Asset(
        task_id=task.id, company_id=company.id, domain="www.example.com",
        ip_address="1.2.3.4", port=443,
    ))
    async_session.add(Asset(
        task_id=task.id, company_id=company.id, domain="other.org",
        ip_address="5.6.7.8", port=443,
    ))
    await async_session.commit()
    return task, company


@pytest.mark.asyncio
async def test_backfill_icp(monkeypatch, async_session, task_company_assets):
    task, company = task_company_assets

    async def fake_query(domain):
        return {"domain": domain, "icp_number": "京ICP备2024000001号-1",
                "icp_entity": "北京示例科技有限公司",
                "provider": "https://api.example.com/icp", "raw": {}}

    monkeypatch.setattr(icp_scraper, "query_icp", fake_query)

    n = await _backfill_icp(async_session, task, company)
    assert n == 1

    await async_session.refresh(company)
    assert company.icp_number == "京ICP备2024000001号-1"
    assert company.icp_entity == "北京示例科技有限公司"

    assets = (await async_session.execute(
        select(Asset).where(Asset.task_id == task.id))).scalars().all()
    www = next(a for a in assets if a.domain == "www.example.com")
    other = next(a for a in assets if a.domain == "other.org")
    assert www.icp_entity == "北京示例科技有限公司"
    assert www.icp_verified is True
    assert other.icp_verified is False  # 非企业域名不被误标

    docs = (await db_docs(async_session, task.id))
    assert len(docs) == 1
    assert "京ICP备2024000001号-1" in docs[0].content
    assert docs[0].source_type == "legal"

    # 幂等：重复回填不产生重复 IntelDocument
    await _backfill_icp(async_session, task, company)
    assert len(await db_docs(async_session, task.id)) == 1


async def db_docs(session, task_id):
    return (await session.execute(
        select(IntelDocument).where(IntelDocument.task_id == task_id))).scalars().all()


@pytest.mark.asyncio
async def test_backfill_icp_no_domains(async_session, task_company_assets):
    task, company = task_company_assets
    company.domains = []
    await async_session.commit()
    assert await _backfill_icp(async_session, task, company) == 0
