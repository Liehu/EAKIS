"""Intelligence API router — M1 情报采集模块.

Endpoints:
  POST  /v1/tasks/{task_id}/intelligence             - 启动情报采集
  GET   /v1/tasks/{task_id}/intelligence             - 获取采集状态
  GET   /v1/tasks/{task_id}/intelligence/documents   - 获取情报文档列表
  GET   /v1/tasks/{task_id}/intelligence/dsl         - 获取 DSL 查询
  GET   /v1/tasks/{task_id}/intelligence/sources     - 获取数据源状态
"""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from src.api.schemas.intelligence import (
    DslListResponse,
    IntelligenceDocumentItem,
    IntelligenceDocumentListResponse,
    IntelligenceStartRequest,
    IntelligenceStartResponse,
    IntelligenceStatusResponse,
    Pagination,
    SourceListResponse,
)
from src.intelligence.config import IntelligenceConfig
from src.intelligence.models import SourceCategory
from src.intelligence.module import IntelligenceModule

router = APIRouter(tags=["intelligence"])

_modules: dict[str, IntelligenceModule] = {}


def _get_or_create_module(task_id: str) -> IntelligenceModule:
    if task_id not in _modules:
        _modules[task_id] = IntelligenceModule(config=IntelligenceConfig())
    return _modules[task_id]


@router.post("/tasks/{task_id}/intelligence", response_model=IntelligenceStartResponse, status_code=201)
async def start_intelligence(
    task_id: UUID,
    body: IntelligenceStartRequest,
) -> IntelligenceStartResponse:
    categories = None
    if body.enabled_categories:
        categories = [SourceCategory(c) for c in body.enabled_categories]

    module = _get_or_create_module(str(task_id))
    result = await module.run(
        task_id=str(task_id),
        company_name=body.company_name,
        industry=body.industry,
        domains=body.domains,
        keywords=body.keywords,
        enabled_categories=categories,
    )

    return IntelligenceStartResponse(
        task_id=task_id,
        status=result.status.value,
        total_sources=result.total_sources,
        total_raw_documents=result.total_documents,
        total_cleaned_documents=result.cleaned_documents,
        avg_quality_score=round(result.avg_quality_score, 2),
        errors=result.errors,
    )


@router.get("/tasks/{task_id}/intelligence", response_model=IntelligenceStatusResponse)
async def get_intelligence_status(
    task_id: UUID,
) -> IntelligenceStatusResponse:
    module = _modules.get(str(task_id))
    if module is None:
        raise HTTPException(status_code=404, detail="No intelligence collection found for this task")

    status = module.get_status()
    return IntelligenceStatusResponse(
        task_id=task_id,
        status=status["status"],
        total_sources=status["total_sources"] if "total_sources" in status else len(status.get("sources", [])),
        total_raw_documents=status["total_raw"],
        total_cleaned_documents=status["total_cleaned"],
        avg_quality_score=round(status.get("avg_quality", 0.0), 2),
        sources=status.get("sources", []),
        dsl_queries=status.get("dsl_queries", []),
    )


@router.get("/tasks/{task_id}/intelligence/documents", response_model=IntelligenceDocumentListResponse)
async def list_intelligence_documents(
    task_id: UUID,
    min_quality: float = Query(default=0.0, ge=0.0, le=1.0),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> IntelligenceDocumentListResponse:
    module = _modules.get(str(task_id))
    if module is None:
        raise HTTPException(status_code=404, detail="No intelligence collection found for this task")

    all_docs = module.get_documents(min_quality=min_quality)
    total = len(all_docs)
    start = (page - 1) * page_size
    end = start + page_size
    page_docs = all_docs[start:end]

    items = [IntelligenceDocumentItem(**d) for d in page_docs]
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return IntelligenceDocumentListResponse(
        data=items,
        pagination=Pagination(page=page, page_size=page_size, total=total, total_pages=total_pages).model_dump(),
    )


@router.get("/tasks/{task_id}/intelligence/dsl", response_model=DslListResponse)
async def get_intelligence_dsl(
    task_id: UUID,
) -> DslListResponse:
    module = _modules.get(str(task_id))
    if module is None:
        raise HTTPException(status_code=404, detail="No intelligence collection found for this task")

    return DslListResponse(data=module.get_dsl_queries())


@router.get("/tasks/{task_id}/intelligence/sources", response_model=SourceListResponse)
async def get_intelligence_sources(
    task_id: UUID,
) -> SourceListResponse:
    module = _modules.get(str(task_id))
    if module is None:
        raise HTTPException(status_code=404, detail="No intelligence collection found for this task")

    return SourceListResponse(data=module.get_sources())
