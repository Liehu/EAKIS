"""Keyword API router — section 9.3 of the API design spec.

Endpoints:
  GET    /v1/tasks/{task_id}/keywords              - List keywords
  POST   /v1/tasks/{task_id}/keywords              - Add keyword
  DELETE /v1/tasks/{task_id}/keywords/{keyword_id} - Delete keyword
"""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
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
