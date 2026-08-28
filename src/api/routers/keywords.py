"""Keyword API router — section 9.3 of the API design spec.

Endpoints:
  GET    /v1/tasks/{task_id}/keywords              - List keywords
  POST   /v1/tasks/{task_id}/keywords              - Add keyword
  DELETE /v1/tasks/{task_id}/keywords/{keyword_id} - Delete keyword
  POST   /v1/tasks/{task_id}/keywords/generate     - 从情报文档生成关键词
  GET    /v1/companies/{company_id}/keywords       - 企业关键词列表
  POST   /v1/companies/{company_id}/keywords       - 添加企业关键词
  DELETE /v1/companies/{company_id}/keywords/{kid} - 删除企业关键词
  POST   /v1/companies/{company_id}/keywords/generate - 从企业任务情报生成关键词
"""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_async_db
from src.api.schemas.keyword import (
    KeywordCreateRequest,
    KeywordDetailResponse,
    KeywordItem,
    KeywordListResponse,
    KeywordSummary,
    Pagination,
)
from src.keywords.module import KeywordModule
from src.models.company import Company
from src.models.keyword import Keyword
from src.models.task import Task

router = APIRouter(tags=["keywords"])


def _module() -> KeywordModule:
    return KeywordModule()


@router.get("/tasks/{task_id}/keywords", response_model=KeywordListResponse)
async def list_keywords(
    task_id: UUID,
    type: str | None = Query(default=None, pattern=r"^(business|tech|entity)$"),
    min_weight: float = Query(default=0.0, ge=0.0, le=1.0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_db),
) -> KeywordListResponse:
    module = _module()
    keywords = await module.get_keywords(
        session, task_id, keyword_type=type, min_weight=min_weight,
        page=page, page_size=page_size,
    )
    counts = await module.get_keyword_count(session, task_id)

    items = [KeywordItem.model_validate(kw) for kw in keywords]
    total = counts["total"]
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return KeywordListResponse(
        data=items,
        summary=KeywordSummary(
            business_count=counts["business"],
            tech_count=counts["tech"],
            entity_count=counts["entity"],
            total=total,
        ),
        pagination=Pagination(
            page=page,
            page_size=page_size,
            total=total,
            total_pages=total_pages,
        ),
    )


@router.post("/tasks/{task_id}/keywords", response_model=KeywordDetailResponse, status_code=201)
async def create_keyword(
    task_id: UUID,
    body: KeywordCreateRequest,
    session: AsyncSession = Depends(get_async_db),
) -> KeywordDetailResponse:
    # Verify task exists
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    module = _module()
    kw = await module.add_keyword(
        session, task_id, body.word, body.type, body.weight, body.reason,
    )
    await session.commit()
    return KeywordDetailResponse.model_validate(kw)


@router.delete("/tasks/{task_id}/keywords/{keyword_id}", status_code=204)
async def delete_keyword(
    task_id: UUID,
    keyword_id: UUID,
    session: AsyncSession = Depends(get_async_db),
):
    module = _module()
    deleted = await module.delete_keyword(session, keyword_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Keyword not found")
    await session.commit()
    return None


# ---------------------------------------------------------------------------
# 关键词生成（从情报文档 → 摘要 → 生成 → 排序 → 扩展 → 持久化）
# ---------------------------------------------------------------------------

@router.post("/tasks/{task_id}/keywords/generate", response_model=KeywordListResponse)
async def generate_keywords(
    task_id: UUID,
    session: AsyncSession = Depends(get_async_db),
) -> KeywordListResponse:
    """从任务的情报文档生成关键词（跑 KeywordModule pipeline）。"""
    task = await session.get(Task, task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    company_name = task.company_name
    industry = task.industry
    company = None
    if task.company_id:
        company = await session.get(Company, task.company_id)
        if company:
            company_name = company.name
            industry = company.industry

    module = KeywordModule(industry=industry)
    generated = await module.run_pipeline(
        session=session, task_id=task_id, company_name=company_name, industry=industry,
    )

    # populate company_id
    if company is not None:
        for kw in generated:
            if kw.company_id is None:
                kw.company_id = company.id
        await session.commit()

    items = [KeywordItem.model_validate(kw) for kw in generated]
    return KeywordListResponse(
        data=items,
        summary=KeywordSummary(total=len(items)),
        pagination=Pagination(page=1, page_size=len(items), total=len(items), total_pages=1),
    )


# ---------------------------------------------------------------------------
# 企业关键词管理（知识库-企业关键词管理）
# ---------------------------------------------------------------------------

@router.get("/companies/{company_id}/keywords", response_model=KeywordListResponse)
async def list_company_keywords(
    company_id: UUID,
    type: str | None = Query(default=None, pattern=r"^(business|tech|entity)$"),
    min_weight: float = Query(default=0.0, ge=0.0, le=1.0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_async_db),
) -> KeywordListResponse:
    """列出企业的关键词（含直接归属 company_id + 企业任务关联的关键词）。"""
    # 企业直接归属的关键词 + 企业下所有任务的关键词
    task_ids_subq = select(Task.id).where(Task.company_id == company_id)
    stmt = select(Keyword).where(
        (Keyword.company_id == company_id) | (Keyword.task_id.in_(task_ids_subq))
    )
    if type:
        stmt = stmt.where(Keyword.type == type)
    if min_weight > 0:
        stmt = stmt.where(Keyword.weight >= min_weight)

    total = (await session.execute(select(func.count()).select_from(stmt.subquery()))).scalar() or 0
    stmt = stmt.order_by(Keyword.weight.desc()).offset((page - 1) * page_size).limit(page_size)
    keywords = (await session.execute(stmt)).scalars().all()
    items = [KeywordItem.model_validate(kw) for kw in keywords]

    # 分类统计
    biz = sum(1 for k in keywords if k.type == "business")
    tech = sum(1 for k in keywords if k.type == "tech")
    ent = sum(1 for k in keywords if k.type == "entity")
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return KeywordListResponse(
        data=items,
        summary=KeywordSummary(business_count=biz, tech_count=tech, entity_count=ent, total=total),
        pagination=Pagination(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


@router.post("/companies/{company_id}/keywords", response_model=KeywordDetailResponse, status_code=201)
async def add_company_keyword(
    company_id: UUID,
    body: KeywordCreateRequest,
    session: AsyncSession = Depends(get_async_db),
) -> KeywordDetailResponse:
    """手动添加企业关键词。"""
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    kw = Keyword(
        task_id=(await session.execute(select(Task.id).where(Task.company_id == company_id).limit(1))).scalar() or company_id,
        company_id=company_id,
        word=body.word,
        type=body.type,
        weight=body.weight,
        confidence=1.0,
        source="manual",
    )
    session.add(kw)
    await session.commit()
    await session.refresh(kw)
    return KeywordDetailResponse.model_validate(kw)


@router.delete("/companies/{company_id}/keywords/{keyword_id}", status_code=204)
async def delete_company_keyword(
    company_id: UUID,
    keyword_id: UUID,
    session: AsyncSession = Depends(get_async_db),
):
    kw = await session.get(Keyword, keyword_id)
    if kw is None or (kw.company_id != company_id):
        raise HTTPException(status_code=404, detail="Keyword not found")
    await session.delete(kw)
    await session.commit()
    return None


@router.post("/companies/{company_id}/keywords/generate", response_model=KeywordListResponse)
async def generate_company_keywords(
    company_id: UUID,
    session: AsyncSession = Depends(get_async_db),
) -> KeywordListResponse:
    """从企业的任务情报文档生成关键词（找企业最新的有情报的任务，跑 pipeline）。"""
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(status_code=404, detail="Company not found")

    # 找企业最新一个有情报文档的任务
    task = (await session.execute(
        select(Task).where(Task.company_id == company_id).order_by(Task.created_at.desc()).limit(1)
    )).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=400, detail="该企业无关联任务，请先创建任务并采集情报")

    module = KeywordModule(industry=company.industry)
    generated = await module.run_pipeline(
        session=session, task_id=task.id, company_name=company.name, industry=company.industry,
    )
    # populate company_id
    for kw in generated:
        if kw.company_id is None:
            kw.company_id = company_id
    await session.commit()

    items = [KeywordItem.model_validate(kw) for kw in generated]
    return KeywordListResponse(
        data=items,
        summary=KeywordSummary(total=len(items)),
        pagination=Pagination(page=1, page_size=len(items), total=len(items), total_pages=1),
    )
