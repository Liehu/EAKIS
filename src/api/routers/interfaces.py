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

from fastapi import APIRouter, HTTPException, Query

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

router = APIRouter(tags=["interfaces"])

_modules: dict[str, ApiCrawlerModule] = {}


def _get_or_create_module(task_id: str) -> ApiCrawlerModule:
    if task_id not in _modules:
        _modules[task_id] = ApiCrawlerModule()
    return _modules[task_id]


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
) -> InterfaceListResponse:
    module = _modules.get(str(task_id))
    if module is None:
        raise HTTPException(status_code=404, detail="No crawl found for this task")

    effective_type = api_type or type
    items = module.get_interfaces(
        asset_id=asset_id,
        api_type=effective_type,
        method=method,
        privilege_sensitive=privilege_sensitive,
        min_priority=min_priority,
        page=page,
        page_size=page_size,
    )

    all_ifaces = module.get_interfaces(page=1, page_size=10000)
    total = len(all_ifaces) if effective_type is None else len(
        [i for i in all_ifaces if i["api_type"] == effective_type]
    )
    by_type: dict[str, int] = {}
    for i in all_ifaces:
        by_type[i["api_type"]] = by_type.get(i["api_type"], 0) + 1

    return InterfaceListResponse(
        data=[InterfaceItem(**i) for i in items],
        summary=InterfaceSummary(
            total=total,
            by_type=by_type,
            privilege_sensitive=len(
                [i for i in all_ifaces if i["privilege_sensitive"]]
            ),
            untested=total,
        ),
        pagination={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": math.ceil(total / page_size) if total else 0,
        },
    )


@router.get(
    "/tasks/{task_id}/interfaces/{interface_id}",
    response_model=InterfaceDetailResponse,
)
async def get_interface_detail(
    task_id: UUID,
    interface_id: str,
) -> InterfaceDetailResponse:
    module = _modules.get(str(task_id))
    if module is None:
        raise HTTPException(status_code=404, detail="No crawl found for this task")

    iface = module.get_interface(interface_id)
    if iface is None:
        raise HTTPException(status_code=404, detail="Interface not found")
    return InterfaceDetailResponse(**iface)


@router.patch(
    "/tasks/{task_id}/interfaces/{interface_id}",
    response_model=InterfaceDetailResponse,
)
async def update_interface(
    task_id: UUID,
    interface_id: str,
    body: InterfaceUpdateRequest,
) -> InterfaceDetailResponse:
    module = _modules.get(str(task_id))
    if module is None:
        raise HTTPException(status_code=404, detail="No crawl found for this task")

    updated = module.update_interface(
        interface_id,
        test_priority=body.test_priority,
        notes=body.notes,
        skip_test=body.skip_test,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Interface not found")
    return InterfaceDetailResponse(**updated)
