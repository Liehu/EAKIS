"""Intelligence API router — M1 情报采集模块.

Endpoints:
  POST  /v1/tasks/{task_id}/intelligence             - 启动情报采集
  GET   /v1/tasks/{task_id}/intelligence             - 获取采集状态
  GET   /v1/tasks/{task_id}/intelligence/documents   - 获取情报文档列表
  GET   /v1/tasks/{task_id}/intelligence/dsl         - 获取 DSL 查询
  GET   /v1/tasks/{task_id}/intelligence/sources     - 获取数据源状态
  POST  /v1/intelligence/rag/search                  - RAG 知识库语义检索
  GET   /v1/intelligence/rag/health                  - RAG 知识库健康检查
"""

from __future__ import annotations

import math
from datetime import datetime
from uuid import UUID


def _to_dt(val) -> datetime | None:
    """将字符串/None 转为 datetime（SQLite DateTime 列不接受字符串）。"""
    if val is None or isinstance(val, datetime):
        return val
    if isinstance(val, str):
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except (ValueError, TypeError):
            return None
    return None

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_async_db
from src.api.schemas.intelligence import (
    DslListResponse,
    IntelligenceDocumentItem,
    IntelligenceDocumentListResponse,
    IntelligenceStartRequest,
    IntelligenceStartResponse,
    IntelligenceStatusResponse,
    Pagination,
    RAGHealthResponse,
    RAGSearchRequest,
    RAGSearchResponse,
    RAGSearchResultItem,
    SourceListResponse,
)
from src.intelligence.config import IntelligenceConfig
from src.intelligence.models import SourceCategory
from src.intelligence.module import IntelligenceModule
from src.intelligence.services.rag_client import create_rag_client
from src.intelligence.services.base import BaseRAGClient
from src.models.company import Company
from src.models.intel_document import IntelDocument
from src.models.task import Task

router = APIRouter(tags=["intelligence"])

_modules: dict[str, IntelligenceModule] = {}
_rag_client: BaseRAGClient | None = None


def _get_rag_client() -> BaseRAGClient:
    global _rag_client
    if _rag_client is None:
        _rag_client = create_rag_client()
    return _rag_client


def _get_or_create_module(task_id: str) -> IntelligenceModule:
    if task_id not in _modules:
        _modules[task_id] = IntelligenceModule(
            config=IntelligenceConfig(),
            rag_client=_get_rag_client(),
        )
    return _modules[task_id]


@router.post("/tasks/{task_id}/intelligence", response_model=IntelligenceStartResponse, status_code=201)
async def start_intelligence(
    task_id: UUID,
    body: IntelligenceStartRequest,
    db: AsyncSession = Depends(get_async_db),
) -> IntelligenceStartResponse:
    # 桥接企业信息：从 Task.company_id 取企业 name/industry/domains 作为情报输入
    task = await db.get(Task, task_id)
    company = None
    if task and task.company_id:
        company = await db.get(Company, task.company_id)

    company_name = body.company_name or (company.name if company else (task.company_name if task else ""))
    industry = body.industry or (company.industry if company else (task.industry if task else None))
    domains = body.domains or (company.domains if company else None)
    keywords = body.keywords or (company.aliases if company else None)

    categories = None
    if body.enabled_categories:
        categories = [SourceCategory(c) for c in body.enabled_categories]

    module = _get_or_create_module(str(task_id))
    result = await module.run(
        task_id=str(task_id),
        company_name=company_name,
        industry=industry,
        domains=domains,
        keywords=keywords,
        enabled_categories=categories,
    )

    # 持久化 CleanedDocument → IntelDocument（get_documents 返回 dict）
    saved = 0
    for doc in module.get_documents():
        checksum = doc.get("checksum") if isinstance(doc, dict) else getattr(doc, "checksum", "")
        if not checksum:
            continue
        existing = (await db.execute(
            select(IntelDocument).where(IntelDocument.checksum == checksum).limit(1)
        )).scalar_one_or_none()
        if existing is None:
            db.add(IntelDocument(
                task_id=task_id,
                source_type=doc.get("source_type") if isinstance(doc, dict) else doc.source_type.value,
                source_name=doc.get("source_name") if isinstance(doc, dict) else doc.source_name,
                source_url=doc.get("source_url") if isinstance(doc, dict) else doc.source_url,
                content=doc.get("content") if isinstance(doc, dict) else doc.content,
                quality_score=doc.get("quality_score", 0.0) if isinstance(doc, dict) else doc.quality_score,
                published_at=_to_dt(doc.get("published_at") if isinstance(doc, dict) else doc.published_at),
                entities=doc.get("entities", []) if isinstance(doc, dict) else doc.entities,
                checksum=checksum,
            ))
            saved += 1
    await db.commit()

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


# --- RAG knowledge base endpoints ---


@router.post("/intelligence/rag/search", response_model=RAGSearchResponse)
async def search_rag(
    body: RAGSearchRequest,
) -> RAGSearchResponse:
    """Semantic search across the RAG knowledge base."""
    rag_filter: dict | None = None
    if body.task_id or body.source_type or body.min_quality is not None:
        rag_filter = {}
        if body.task_id:
            rag_filter["task_id"] = body.task_id
        if body.source_type:
            rag_filter["source_type"] = body.source_type
        if body.min_quality is not None:
            rag_filter["min_quality"] = body.min_quality

    client = _get_rag_client()
    results = await client.search(query=body.query, top_k=body.top_k, filter=rag_filter)

    items = [RAGSearchResultItem(**r) for r in results]
    return RAGSearchResponse(data=items, total=len(items))


@router.get("/intelligence/rag/health", response_model=RAGHealthResponse)
async def rag_health() -> RAGHealthResponse:
    """Health check for the RAG knowledge base."""
    client = _get_rag_client()
    if not hasattr(client, "health_check"):
        return RAGHealthResponse(status="healthy", collection="stub")
    health = await client.health_check()
    return RAGHealthResponse(**health)
