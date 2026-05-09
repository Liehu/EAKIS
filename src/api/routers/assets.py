"""Asset API router - M3.

Endpoints:
  POST  /v1/tasks/{task_id}/assets/discover            - start discovery
  GET   /v1/tasks/{task_id}/assets/status              - get discovery status
  GET   /v1/tasks/{task_id}/assets                     - list assets
  GET   /v1/tasks/{task_id}/assets/{asset_id}          - get asset detail
  PATCH /v1/tasks/{task_id}/assets/{asset_id}          - update asset
"""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query

from src.api.schemas.asset import (
    AssetDetailResponse,
    AssetItem,
    AssetListResponse,
    AssetUpdateRequest,
    DiscoveryStartRequest,
    DiscoveryStartResponse,
    DiscoveryStatusResponse,
)
from src.asset_discovery.module import AssetDiscoveryModule

router = APIRouter(tags=["assets"])

_modules: dict[str, AssetDiscoveryModule] = {}


def _get_or_create_module(task_id: str) -> AssetDiscoveryModule:
    if task_id not in _modules:
        _modules[task_id] = AssetDiscoveryModule()
    return _modules[task_id]


@router.post(
    "/tasks/{task_id}/assets/discover",
    response_model=DiscoveryStartResponse,
    status_code=201,
)
async def start_discovery(
    task_id: UUID,
    body: DiscoveryStartRequest,
) -> DiscoveryStartResponse:
    module = _get_or_create_module(str(task_id))
    result = await module.run(
        task_id=str(task_id),
        dsl_queries=body.dsl_queries,
        company_name=body.company_name,
        target_domains=body.target_domains,
        target_icp_entity=body.target_icp_entity,
        target_ip_ranges=body.target_ip_ranges,
    )
    return DiscoveryStartResponse(
        task_id=str(task_id),
        status=result.status.value,
        total_searched=result.total_searched,
        total_candidates=result.total_candidates,
        total_confirmed=result.total_confirmed,
        total_enriched=result.total_enriched,
        by_asset_type=result.by_asset_type,
        avg_confidence=result.avg_confidence,
        errors=result.errors,
    )


@router.get(
    "/tasks/{task_id}/assets/status",
    response_model=DiscoveryStatusResponse,
)
async def get_discovery_status(task_id: UUID) -> DiscoveryStatusResponse:
    module = _modules.get(str(task_id))
    if module is None:
        raise HTTPException(status_code=404, detail="No asset discovery found for this task")
    return DiscoveryStatusResponse(**module.get_status())


@router.get("/tasks/{task_id}/assets", response_model=AssetListResponse)
async def list_assets(
    task_id: UUID,
    risk: str | None = Query(default=None, pattern="^(critical|high|medium|low|info)$"),
    confirmed: bool | None = Query(default=None),
    asset_type: str | None = Query(default=None),
    icp_verified: bool | None = Query(default=None),
    has_waf: bool | None = Query(default=None),
    tech_stack: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
) -> AssetListResponse:
    module = _modules.get(str(task_id))
    if module is None:
        raise HTTPException(status_code=404, detail="No asset discovery found for this task")

    items, total = module.get_assets(
        risk=risk,
        confirmed=confirmed,
        asset_type=asset_type,
        icp_verified=icp_verified,
        has_waf=has_waf,
        tech_stack=tech_stack,
        page=page,
        page_size=page_size,
    )

    return AssetListResponse(
        data=[AssetItem(**i) for i in items],
        pagination={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": math.ceil(total / page_size) if total else 0,
        },
    )


@router.get(
    "/tasks/{task_id}/assets/{asset_id}",
    response_model=AssetDetailResponse,
)
async def get_asset_detail(
    task_id: UUID,
    asset_id: str,
) -> AssetDetailResponse:
    module = _modules.get(str(task_id))
    if module is None:
        raise HTTPException(status_code=404, detail="No asset discovery found for this task")

    asset = module.get_asset(asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return AssetDetailResponse(**asset)


@router.patch(
    "/tasks/{task_id}/assets/{asset_id}",
    response_model=AssetDetailResponse,
)
async def update_asset(
    task_id: UUID,
    asset_id: str,
    body: AssetUpdateRequest,
) -> AssetDetailResponse:
    module = _modules.get(str(task_id))
    if module is None:
        raise HTTPException(status_code=404, detail="No asset discovery found for this task")

    updated = module.update_asset(
        asset_id,
        confirmed=body.confirmed,
        risk_level=body.risk_level,
        notes=body.notes,
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Asset not found")
    return AssetDetailResponse(**updated)
