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

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.dependencies import get_async_db
from src.api.schemas.asset import (
    AssetDetailResponse,
    AssetItem,
    AssetListResponse,
    AssetUpdateRequest,
    DiscoveryStartRequest,
    DiscoveryStartResponse,
    DiscoveryStatusResponse,
    TypedAssetItem,
    TypedAssetListResponse,
)
from src.asset_discovery.module import AssetDiscoveryModule
from src.models.asset import Asset
from src.models.asset_types import (
    IPAsset, DomainAsset, Certificate, MiniProgramAsset, AppAsset,
)
from src.models.company import Company
from src.models.vulnerability import Vulnerability

router = APIRouter(tags=["assets"])

_modules: dict[str, AssetDiscoveryModule] = {}


def _get_or_create_module(task_id: str) -> AssetDiscoveryModule:
    if task_id not in _modules:
        _modules[task_id] = AssetDiscoveryModule()
    return _modules[task_id]


def _asset_to_item(a: Asset) -> AssetItem:
    """Convert ORM Asset to schema AssetItem."""
    cert_info = a.cert_info if isinstance(a.cert_info, dict) else {}
    return AssetItem(
        id=str(a.id),
        domain=a.domain,
        ip_address=str(a.ip_address) if a.ip_address else None,
        port=a.port,
        protocol=a.protocol or "https",
        asset_type=a.asset_type or "web",
        confidence=a.confidence_score or 0.0,
        risk_level=a.risk_level.value if hasattr(a.risk_level, 'value') else (a.risk_level or "info"),
        icp_verified=a.icp_verified or False,
        icp_entity=a.icp_entity,
        waf_detected=a.waf_type,
        tech_stack=a.tech_stack or [],
        open_ports=a.open_ports or [],
        cert_info=cert_info if cert_info else {},
        screenshot_path=a.screenshot_path,
        confirmed=a.confirmed or False,
        notes=a.notes,
        discovered_at=str(a.discovered_at) if a.discovered_at else None,
    )


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
    db: AsyncSession = Depends(get_async_db),
) -> AssetListResponse:
    stmt = select(Asset).where(Asset.task_id == task_id)
    count_stmt = select(func.count(Asset.id)).where(Asset.task_id == task_id)

    if risk:
        stmt = stmt.where(Asset.risk_level == risk)
        count_stmt = count_stmt.where(Asset.risk_level == risk)
    if confirmed is not None:
        stmt = stmt.where(Asset.confirmed.is_(confirmed))
        count_stmt = count_stmt.where(Asset.confirmed.is_(confirmed))
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type)
        count_stmt = count_stmt.where(Asset.asset_type == asset_type)
    if icp_verified is not None:
        stmt = stmt.where(Asset.icp_verified.is_(icp_verified))
        count_stmt = count_stmt.where(Asset.icp_verified.is_(icp_verified))
    if has_waf is not None:
        if has_waf:
            stmt = stmt.where(Asset.waf_type.isnot(None))
            count_stmt = count_stmt.where(Asset.waf_type.isnot(None))
        else:
            stmt = stmt.where(Asset.waf_type.is_(None))
            count_stmt = count_stmt.where(Asset.waf_type.is_(None))

    total = (await db.execute(count_stmt)).scalar() or 0
    total_pages = max(1, math.ceil(total / page_size))

    stmt = stmt.order_by(Asset.discovered_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    assets = result.scalars().all()

    return AssetListResponse(
        data=[_asset_to_item(a) for a in assets],
        pagination={
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        },
    )


@router.get(
    "/tasks/{task_id}/assets/{asset_id}",
    response_model=AssetDetailResponse,
)
async def get_asset_detail(
    task_id: UUID,
    asset_id: str,
    db: AsyncSession = Depends(get_async_db),
) -> AssetDetailResponse:
    from sqlalchemy import select as sa_select
    asset = await db.get(Asset, asset_id)
    if asset is None or str(asset.task_id) != str(task_id):
        raise HTTPException(status_code=404, detail="Asset not found")
    item = _asset_to_item(asset)
    return AssetDetailResponse(
        **item.model_dump(),
    )


@router.patch(
    "/tasks/{task_id}/assets/{asset_id}",
    response_model=AssetDetailResponse,
)
async def update_asset(
    task_id: UUID,
    asset_id: str,
    body: AssetUpdateRequest,
    db: AsyncSession = Depends(get_async_db),
) -> AssetDetailResponse:
    asset = await db.get(Asset, asset_id)
    if asset is None or str(asset.task_id) != str(task_id):
        raise HTTPException(status_code=404, detail="Asset not found")

    if body.confirmed is not None:
        asset.confirmed = body.confirmed
    if body.risk_level is not None:
        asset.risk_level = body.risk_level
    if body.notes is not None:
        asset.notes = body.notes

    await db.commit()
    await db.refresh(asset)
    item = _asset_to_item(asset)
    return AssetDetailResponse(
        **item.model_dump(),
    )


# ── 全局资产视图 (S1 资产多表 + 类型专属字段) ─────────────
# 用于资产管理页: 按 asset_type 过滤, JOIN 类型子表返回专属字段.
# 与 task 维度端点不同, 这是全局视图 (不限任务), 支持 company_id 过滤.

_TYPE_MODELS = {
    "ip": IPAsset,
    "domain": DomainAsset,
    "certificate": Certificate,
    "miniprogram": MiniProgramAsset,
    "app": AppAsset,
}


async def _load_type_specific(db: AsyncSession, asset_id, asset_type: str) -> dict:
    """加载类型专属字段 (从子表)."""
    Model = _TYPE_MODELS.get(asset_type)
    if Model is None:
        return {}  # web 无子表
    row = await db.get(Model, asset_id)
    if row is None:
        return {}
    d = {c.name: getattr(row, c.name) for c in row.__table__.columns}
    # 过滤 asset_id (主键, 与 Asset.id 重复) 和时间戳
    d.pop("asset_id", None)
    d.pop("updated_at", None)
    # datetime → iso
    for k, v in list(d.items()):
        if hasattr(v, "isoformat"):
            d[k] = v.isoformat()
        if isinstance(v, bool):
            d[k] = v
    return d


@router.get("/assets", response_model=TypedAssetListResponse)
async def list_typed_assets(
    asset_type: str | None = Query(default=None, description="ip/domain/web/app/miniprogram/certificate"),
    company_id: UUID | None = Query(default=None),
    risk: str | None = Query(default=None),
    confirmed: bool | None = Query(default=None),
    q: str | None = Query(default=None, description="domain/ip 模糊"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
) -> TypedAssetListResponse:
    """全局资产列表 (按类型 + 类型专属字段). 用于资产管理页 6 类 Tab."""
    stmt = select(Asset)
    count_stmt = select(func.count(Asset.id))
    if asset_type:
        stmt, count_stmt = (stmt.where(Asset.asset_type == asset_type),
                            count_stmt.where(Asset.asset_type == asset_type))
    if company_id:
        stmt, count_stmt = (stmt.where(Asset.company_id == company_id),
                            count_stmt.where(Asset.company_id == company_id))
    if risk:
        stmt, count_stmt = (stmt.where(Asset.risk_level == risk),
                            count_stmt.where(Asset.risk_level == risk))
    if confirmed is not None:
        stmt, count_stmt = (stmt.where(Asset.confirmed.is_(confirmed)),
                            count_stmt.where(Asset.confirmed.is_(confirmed)))
    if q:
        like = f"%{q}%"
        from sqlalchemy import or_
        stmt, count_stmt = (stmt.where(or_(Asset.domain.ilike(like), Asset.ip_address.ilike(like))),
                            count_stmt.where(or_(Asset.domain.ilike(like), Asset.ip_address.ilike(like))))

    total = (await db.execute(count_stmt)).scalar() or 0
    total_pages = max(1, math.ceil(total / page_size))
    stmt = stmt.order_by(Asset.discovered_at.desc()).offset((page - 1) * page_size).limit(page_size)
    assets = (await db.execute(stmt)).scalars().all()

    # 预加载 company name (批量)
    company_ids = {a.company_id for a in assets if a.company_id}
    company_map: dict = {}
    if company_ids:
        comps = (await db.execute(select(Company).where(Company.id.in_(company_ids)))).scalars().all()
        company_map = {c.id: c.name for c in comps}

    # 预加载 vuln_count (按 asset 批量)
    asset_ids = [a.id for a in assets]
    vuln_map: dict = {}
    if asset_ids:
        rows = (await db.execute(
            select(Vulnerability.asset_id, Vulnerability.severity)
            .where(Vulnerability.asset_id.in_(asset_ids))
        )).all()
        for aid, sev in rows:
            d = vuln_map.setdefault(str(aid), {"critical": 0, "high": 0, "medium": 0, "low": 0})
            if sev in d:
                d[sev] += 1

    items: list[TypedAssetItem] = []
    for a in assets:
        type_specific = await _load_type_specific(db, a.id, a.asset_type or "")
        items.append(TypedAssetItem(
            id=str(a.id), asset_type=a.asset_type or "web",
            domain=a.domain, ip_address=a.ip_address, port=a.port,
            risk_level=a.risk_level or "info", confidence=a.confidence_score or 0.0,
            confirmed=a.confirmed, company_id=str(a.company_id) if a.company_id else None,
            company_name=company_map.get(a.company_id) if a.company_id else None,
            tech_stack=a.tech_stack or [], icp_entity=a.icp_entity, waf_type=a.waf_type,
            status=a.status or "discovered", notes=a.notes,
            discovered_at=a.discovered_at.isoformat() if a.discovered_at else None,
            vuln_count=vuln_map.get(str(a.id), {"critical": 0, "high": 0, "medium": 0, "low": 0}),
            type_specific=type_specific,
        ))

    return TypedAssetListResponse(
        data=items,
        pagination={"page": page, "page_size": page_size, "total": total, "total_pages": total_pages},
    )


@router.get("/assets/{asset_id}/full")
async def get_asset_full(
    asset_id: UUID,
    db: AsyncSession = Depends(get_async_db),
) -> dict:
    """资产完整详情: 公共字段 + 类型专属字段 + 关联漏洞 + 关联域名/IP + 关联单位.
    用于资产详情 Drawer."""
    asset = await db.get(Asset, asset_id)
    if asset is None:
        raise HTTPException(status_code=404, detail="资产不存在")

    type_specific = await _load_type_specific(db, asset.id, asset.asset_type or "")
    # 关联漏洞
    vulns = (await db.execute(
        select(Vulnerability).where(Vulnerability.asset_id == asset_id)
    )).scalars().all()
    # 关联单位
    company_name = None
    if asset.company_id:
        company = await db.get(Company, asset.company_id)
        company_name = company.name if company else None

    return {
        "id": str(asset.id), "asset_type": asset.asset_type,
        "domain": asset.domain, "ip_address": asset.ip_address, "port": asset.port,
        "risk_level": asset.risk_level, "confirmed": asset.confirmed,
        "company_id": str(asset.company_id) if asset.company_id else None,
        "company_name": company_name,
        "tech_stack": asset.tech_stack or [], "icp_entity": asset.icp_entity,
        "waf_type": asset.waf_type, "open_ports": asset.open_ports or [],
        "cert_info": asset.cert_info or {}, "notes": asset.notes,
        "status": asset.status, "value_score": asset.value_score,
        "discovered_at": asset.discovered_at.isoformat() if asset.discovered_at else None,
        "type_specific": type_specific,
        "vulnerabilities": [
            {"id": str(v.id), "title": getattr(v, "title", None), "severity": v.severity,
             "vuln_type": getattr(v, "vuln_type", None), "status": getattr(v, "status", None)}
            for v in vulns
        ],
    }
