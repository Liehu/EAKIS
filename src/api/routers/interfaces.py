"""Interface API router - M4.

Endpoints:
  POST  /v1/tasks/{task_id}/interfaces/crawl          - start crawl
  GET   /v1/tasks/{task_id}/interfaces/status         - get crawl status
  GET   /v1/tasks/{task_id}/interfaces                - list interfaces
  GET   /v1/tasks/{task_id}/interfaces/{interface_id} - get interface detail
  PATCH /v1/tasks/{task_id}/interfaces/{interface_id} - update interface
"""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_async_db
from src.api.schemas.interface import (
    CrawlStartRequest,
    CrawlStartResponse,
    CrawlStatusResponse,
    InterfaceDetailResponse,
    InterfaceItem,
    InterfaceListResponse,
    InterfaceSummary,
    InterfaceUpdateRequest,
)
from src.api_crawler.module import ApiCrawlerModule
from src.models.interface import ApiInterface

router = APIRouter(tags=["interfaces"])

_modules: dict[str, ApiCrawlerModule] = {}


def _get_or_create_module(task_id: str) -> ApiCrawlerModule:
    if task_id not in _modules:
        _modules[task_id] = ApiCrawlerModule()
    return _modules[task_id]


def _iface_to_item(i: ApiInterface) -> InterfaceItem:
    """Convert ORM ApiInterface to schema InterfaceItem."""
    params = i.parameters if isinstance(i.parameters, list) else []
    return InterfaceItem(
        interface_id=str(i.id),
        asset_id=str(i.asset_id),
        path=i.path,
        path_pattern=i.path_pattern or "",
        method=i.method,
        api_type=i.api_type or "",
        parameters=params,
        request_headers=i.request_headers or {},
        response_schema=i.response_schema or {},
        auth_required=i.auth_required or False,
        privilege_sensitive=i.privilege_sensitive or False,
        sensitive_params=i.sensitive_params or [],
        trigger_scenario=i.trigger_scenario,
        test_priority=i.test_priority or 5,
        crawl_method=i.crawl_method or "static",
        version=i.version or 1,
        checksum=i.checksum or "",
        vuln_tested=False,
        vuln_count=0,
        skip_test=i.skip_test or False,
        notes=i.notes,
    )


@router.post(
    "/tasks/{task_id}/interfaces/crawl",
    response_model=CrawlStartResponse,
    status_code=201,
)
async def start_crawl(
    task_id: UUID,
    body: CrawlStartRequest,
) -> CrawlStartResponse:
    module = _get_or_create_module(str(task_id))
    result = await module.run(task_id=str(task_id), assets=body.assets)
    return CrawlStartResponse(
        task_id=str(task_id),
        status=result.status.value,
        total_assets=result.total_assets,
        total_raw=result.total_raw,
        total_classified=result.total_classified,
        by_type=result.by_type,
        privilege_sensitive_count=result.privilege_sensitive_count,
        errors=result.errors,
    )


@router.get("/tasks/{task_id}/interfaces/status", response_model=CrawlStatusResponse)
async def get_crawl_status(task_id: UUID) -> CrawlStatusResponse:
    module = _modules.get(str(task_id))
    if module is None:
        raise HTTPException(status_code=404, detail="No crawl found for this task")
    status = module.get_status()
    return CrawlStatusResponse(**status)


@router.get("/tasks/{task_id}/interfaces", response_model=InterfaceListResponse)
async def list_interfaces(
    task_id: UUID,
    asset_id: str | None = Query(default=None),
    type: str | None = Query(default=None),
    api_type: str | None = Query(default=None),
    method: str | None = Query(default=None),
    privilege_sensitive: bool | None = Query(default=None),
    min_priority: int | None = Query(default=None, ge=1, le=10),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
) -> InterfaceListResponse:
    stmt = select(ApiInterface).where(ApiInterface.task_id == task_id)
    count_stmt = select(func.count(ApiInterface.id)).where(ApiInterface.task_id == task_id)

    effective_type = api_type or type
    if effective_type:
        stmt = stmt.where(ApiInterface.api_type == effective_type)
        count_stmt = count_stmt.where(ApiInterface.api_type == effective_type)
    if method:
        stmt = stmt.where(ApiInterface.method == method)
        count_stmt = count_stmt.where(ApiInterface.method == method)
    if asset_id:
        stmt = stmt.where(ApiInterface.asset_id == asset_id)
        count_stmt = count_stmt.where(ApiInterface.asset_id == asset_id)
    if privilege_sensitive is not None:
        stmt = stmt.where(ApiInterface.privilege_sensitive.is_(privilege_sensitive))
        count_stmt = count_stmt.where(ApiInterface.privilege_sensitive.is_(privilege_sensitive))
    if min_priority is not None:
        stmt = stmt.where(ApiInterface.test_priority >= min_priority)
        count_stmt = count_stmt.where(ApiInterface.test_priority >= min_priority)

    total = (await db.execute(count_stmt)).scalar() or 0
    total_pages = max(1, math.ceil(total / page_size))

    stmt = stmt.order_by(ApiInterface.test_priority.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    ifaces = result.scalars().all()

    # Summary
    all_types = (await db.execute(
        select(ApiInterface.api_type, func.count(ApiInterface.id))
        .where(ApiInterface.task_id == task_id)
        .group_by(ApiInterface.api_type)
    )).all()
    by_type = {str(t): c for t, c in all_types}
    priv_count = (await db.scalar(
        select(func.count(ApiInterface.id)).where(
            ApiInterface.task_id == task_id, ApiInterface.privilege_sensitive.is_(True)
        )
    )) or 0

    return InterfaceListResponse(
        data=[_iface_to_item(i) for i in ifaces],
        summary=InterfaceSummary(
            total=total,
            by_type=by_type,
            privilege_sensitive=priv_count,
            untested=total,
        ),
        pagination={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    )


@router.get(
    "/tasks/{task_id}/interfaces/{interface_id}",
    response_model=InterfaceDetailResponse,
)
async def get_interface_detail(
    task_id: UUID,
    interface_id: str,
    db: AsyncSession = Depends(get_async_db),
) -> InterfaceDetailResponse:
    iface = await db.get(ApiInterface, interface_id)
    if iface is None or str(iface.task_id) != str(task_id):
        raise HTTPException(status_code=404, detail="Interface not found")
    item = _iface_to_item(iface)
    return InterfaceDetailResponse(**item.model_dump(), confidence=1.0)


@router.patch(
    "/tasks/{task_id}/interfaces/{interface_id}",
    response_model=InterfaceDetailResponse,
)
async def update_interface(
    task_id: UUID,
    interface_id: str,
    body: InterfaceUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
) -> InterfaceDetailResponse:
    iface = await db.get(ApiInterface, interface_id)
    if iface is None or str(iface.task_id) != str(task_id):
        raise HTTPException(status_code=404, detail="Interface not found")

    if body.test_priority is not None:
        iface.test_priority = body.test_priority
    if body.notes is not None:
        iface.notes = body.notes
    if body.skip_test is not None:
        iface.skip_test = body.skip_test

    await db.commit()
    await db.refresh(iface)
    item = _iface_to_item(iface)
    return InterfaceDetailResponse(**item.model_dump(), confidence=1.0)
