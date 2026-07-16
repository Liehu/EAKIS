"""Companies API router (A.1 企业关系穿透 + A.7 风险).

Endpoints:
  CRUD:
    POST   /v1/companies
    GET    /v1/companies
    GET    /v1/companies/{id}
    PATCH  /v1/companies/{id}
    DELETE /v1/companies/{id}
  Relations (A.1):
    POST   /v1/companies/{id}/relations
    GET    /v1/companies/{id}/relations        (configurable depth + holding threshold)
  Cascade (A.1 + Companies/Detail de-mock):
    GET    /v1/companies/{id}/assets
    GET    /v1/companies/{id}/vulnerabilities
  Graph (A.1-决策6 ECharts):
    GET    /v1/companies/{id}/graph
  Risk (A.7):
    GET    /v1/companies/{id}/risk
    GET    /v1/companies/{id}/risk/trend
  Search (C.3-决策4 简称模糊匹配):
    GET    /v1/companies/search?q=
  Detail (聚合视图，消除前端 mock 依赖):
    GET    /v1/companies/{id}/detail
  Enrichment (商业 API 采集，A.1 企业关系穿透):
    POST   /v1/companies/{id}/enrich
    POST   /v1/companies/{id}/enrich/confirm
    POST   /v1/companies/enrich/batch
    GET    /v1/companies/enrich/providers
"""

from __future__ import annotations

import math
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import UserInfo
from src.api.dependencies import get_async_db
from src.api.deps.permissions import PermissionAction, require_permission
from src.api.schemas.company import (
    AssetTypeSummary,
    BatchEnrichItemResult,
    BatchEnrichRequest,
    BatchEnrichResponse,
    CompanyCreateRequest,
    CompanyDetailResponse,
    CompanyGraphResponse,
    CompanyListResponse,
    CompanyRelationCreateRequest,
    CompanyRelationResponse,
    CompanyResponse,
    CompanyRiskResponse,
    CompanySearchResponse,
    CompanySearchHit,
    CompanyUpdateRequest,
    EnrichConfirmRequest,
    EnrichConfirmResolution,
    EnrichConfirmResponse,
    EnrichRequest,
    EnrichmentResponse,
    FieldConflictItem,
    GraphEdge,
    GraphNode,
    Pagination,
    RiskTrendPoint,
    RiskTrendResponse,
    SubCompanyView,
    VulnSummary,
)
from src.company_enrichment import apply_merge, get_provider, list_providers, plan_company_merge
from src.company_enrichment.base import CompanyEnrichmentProvider
from src.company_enrichment.models import EnrichmentResult, NormalizedCompany
from src.core.risk import calc_company_risk, severity_counts
from src.models.asset import Asset
from src.models.asset_meta import RiskHistory
from src.models.company import Company, CompanyRelation
from src.models.task import Task
from src.models.vulnerability import Vulnerability

router = APIRouter(tags=["companies"])


def _company_to_response(c: Company, task_count: int = 0, latest_status: str | None = None) -> CompanyResponse:
    return CompanyResponse(
        id=c.id,
        org_id=c.org_id,
        name=c.name,
        aliases=c.aliases,
        credit_code=c.credit_code,
        industry=c.industry,
        registered_capital=c.registered_capital,
        established_at=c.established_at,
        legal_person=c.legal_person,
        business_status=c.business_status,
        website=c.website,
        logo_url=c.logo_url,
        email_domains=c.email_domains,
        work_id_rule=c.work_id_rule,
        keywords=c.keywords,
        domains=c.domains,
        ip_ranges=c.ip_ranges,
        notes=c.notes,
        data_source=c.data_source,
        last_collected_at=c.last_collected_at,
        created_at=c.created_at,
        updated_at=c.updated_at,
        task_count=task_count,
        latest_task_status=latest_status,
    )


# ── CRUD ─────────────────────────────────────────────────
@router.post("/companies", response_model=CompanyResponse, status_code=status.HTTP_201_CREATED)
async def create_company(
    body: CompanyCreateRequest,
    enrich: bool = Query(default=False, description="创建后自动从商业API采集关联企业"),
    provider: str = Query(default="yuntu"),
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_CREATE)),
    db: AsyncSession = Depends(get_async_db),
) -> CompanyResponse:
    org_id = body.org_id or UUID(user.org_id)
    company = Company(org_id=org_id, **body.model_dump(exclude={"org_id"}))
    db.add(company)
    await db.commit()
    await db.refresh(company)
    # 可选：创建后自动采集关联企业（auto_fill 策略，仅填充空字段，冲突不落库）
    if enrich:
        try:
            await _do_enrich(db, company, provider=provider, strategy="auto_fill")
        except Exception as exc:  # noqa: BLE001
            # 采集失败不影响企业创建，仅记录日志
            import logging
            logging.getLogger("eakis.companies").warning("创建后自动采集失败（忽略）: %s", exc)
            await db.rollback()
    return _company_to_response(company)


@router.get("/companies", response_model=CompanyListResponse)
async def list_companies(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    q: str | None = Query(default=None, description="名称/简称/信用代码模糊搜索"),
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> CompanyListResponse:
    org_id = UUID(user.org_id)
    stmt = select(Company).where(Company.org_id == org_id)
    count_stmt = select(func.count(Company.id)).where(Company.org_id == org_id)
    if q:
        like = f"%{q}%"
        cond = or_(Company.name.ilike(like), Company.credit_code.ilike(like))
        # aliases is an array; JSON/ARRAY ilike varies by dialect, keep simple name/credit match
        stmt = stmt.where(cond)
        count_stmt = count_stmt.where(cond)

    total = (await db.execute(count_stmt)).scalar() or 0
    total_pages = max(1, math.ceil(total / page_size))
    stmt = stmt.order_by(Company.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    companies = (await db.execute(stmt)).scalars().all()

    return CompanyListResponse(
        data=[_company_to_response(c) for c in companies],
        pagination=Pagination(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


async def _get_owned_company(db: AsyncSession, company_id: UUID, org_id: UUID) -> Company:
    company = await db.get(Company, company_id)
    if company is None or company.org_id != org_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return company


# ── Search (C.3-决策4 简称模糊匹配) — MUST precede /{company_id} route ──
@router.get("/companies/search", response_model=CompanySearchResponse)
async def search_companies(
    q: str = Query(..., min_length=1, max_length=100),
    limit: int = Query(default=10, ge=1, le=50),
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> CompanySearchResponse:
    org_id = UUID(user.org_id)
    like = f"%{q}%"
    rows = (await db.execute(
        select(Company)
        .where(Company.org_id == org_id)
        .where(or_(Company.name.ilike(like), Company.credit_code.ilike(like)))
        .limit(limit)
    )).scalars().all()
    hits = [
        CompanySearchHit(id=c.id, name=c.name, aliases=c.aliases, credit_code=c.credit_code, industry=c.industry)
        for c in rows
    ]
    return CompanySearchResponse(query=q, hits=hits)


@router.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> CompanyResponse:
    company = await _get_owned_company(db, company_id, UUID(user.org_id))
    task_count = (await db.execute(
        select(func.count(Task.id)).where(Task.company_id == company_id)
    )).scalar() or 0
    latest = (await db.execute(
        select(Task.status).where(Task.company_id == company_id).order_by(Task.created_at.desc()).limit(1)
    )).scalar()
    return _company_to_response(company, task_count, latest)


@router.patch("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: UUID,
    body: CompanyUpdateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_UPDATE)),
    db: AsyncSession = Depends(get_async_db),
) -> CompanyResponse:
    company = await _get_owned_company(db, company_id, UUID(user.org_id))
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(company, field, value)
    await db.commit()
    await db.refresh(company)
    return _company_to_response(company)


@router.delete("/companies/{company_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_company(
    company_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_DELETE)),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    company = await _get_owned_company(db, company_id, UUID(user.org_id))
    await db.delete(company)
    await db.commit()


# ── Relations (A.1) ──────────────────────────────────────
@router.post("/companies/{company_id}/relations", response_model=CompanyRelationResponse, status_code=status.HTTP_201_CREATED)
async def add_relation(
    company_id: UUID,
    body: CompanyRelationCreateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_UPDATE)),
    db: AsyncSession = Depends(get_async_db),
) -> CompanyRelationResponse:
    # company_id in path is context; body carries the actual parent/child pair.
    org_id = UUID(user.org_id)
    for cid in (body.parent_company_id, body.child_company_id):
        c = await db.get(Company, cid)
        if c is None or c.org_id != org_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid company {cid}")
    relation = CompanyRelation(**body.model_dump())
    db.add(relation)
    await db.commit()
    await db.refresh(relation)
    return CompanyRelationResponse.model_validate(relation)


@router.get("/companies/{company_id}/relations", response_model=list[CompanyRelationResponse])
async def list_relations(
    company_id: UUID,
    direction: str = Query(default="children", pattern="^(children|parents|both)$"),
    relation_type: str | None = Query(default=None),
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> list[CompanyRelationResponse]:
    await _get_owned_company(db, company_id, UUID(user.org_id))
    stmt = select(CompanyRelation)
    conds = []
    if direction in ("children", "both"):
        conds.append(CompanyRelation.parent_company_id == company_id)
    if direction in ("parents", "both"):
        conds.append(CompanyRelation.child_company_id == company_id)
    stmt = stmt.where(or_(*conds))
    if relation_type:
        stmt = stmt.where(CompanyRelation.relation_type == relation_type)
    rows = (await db.execute(stmt)).scalars().all()
    return [CompanyRelationResponse.model_validate(r) for r in rows]


# ── Cascade queries (de-mock Companies/Detail) ───────────
@router.get("/companies/{company_id}/assets")
async def list_company_assets(
    company_id: UUID,
    asset_type: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_READ)),
    db: AsyncSession = Depends(get_async_db),
):
    await _get_owned_company(db, company_id, UUID(user.org_id))
    stmt = select(Asset).where(Asset.company_id == company_id)
    count_stmt = select(func.count(Asset.id)).where(Asset.company_id == company_id)
    if asset_type:
        stmt = stmt.where(Asset.asset_type == asset_type)
        count_stmt = count_stmt.where(Asset.asset_type == asset_type)
    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(Asset.discovered_at.desc()).offset((page - 1) * page_size).limit(page_size)
    assets = (await db.execute(stmt)).scalars().all()
    return {
        "data": assets,
        "pagination": {
            "page": page, "page_size": page_size, "total": total,
            "total_pages": max(1, math.ceil(total / page_size)),
        },
    }


@router.get("/companies/{company_id}/vulnerabilities")
async def list_company_vulnerabilities(
    company_id: UUID,
    severity: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_READ)),
    db: AsyncSession = Depends(get_async_db),
):
    await _get_owned_company(db, company_id, UUID(user.org_id))
    # Join vulns via assets owned by the company.
    stmt = (
        select(Vulnerability)
        .join(Asset, Vulnerability.asset_id == Asset.id)
        .where(Asset.company_id == company_id)
    )
    count_stmt = (
        select(func.count(Vulnerability.id))
        .join(Asset, Vulnerability.asset_id == Asset.id)
        .where(Asset.company_id == company_id)
    )
    if severity:
        stmt = stmt.where(Vulnerability.severity == severity)
        count_stmt = count_stmt.where(Vulnerability.severity == severity)
    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(Vulnerability.discovered_at.desc()).offset((page - 1) * page_size).limit(page_size)
    vulns = (await db.execute(stmt)).scalars().all()
    return {
        "data": vulns,
        "pagination": {
            "page": page, "page_size": page_size, "total": total,
            "total_pages": max(1, math.ceil(total / page_size)),
        },
    }


# ── Graph (A.1-决策6 ECharts) ────────────────────────────
@router.get("/companies/{company_id}/graph", response_model=CompanyGraphResponse)
async def company_graph(
    company_id: UUID,
    depth: int = Query(default=3, ge=1, le=10, description="向下穿透深度"),
    holding_ratio_min: float = Query(default=51.0, ge=0, le=100, description="持股阈值"),
    include_minority: bool = Query(default=False, description="是否含参股"),
    include_parents: bool = Query(default=True, description="是否包含上级母公司（保持上下文关联）"),
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> CompanyGraphResponse:
    root = await _get_owned_company(db, company_id, UUID(user.org_id))
    org_id = UUID(user.org_id)

    nodes: dict[str, GraphNode] = {
        str(root.id): GraphNode(id=str(root.id), name=root.name, depth=0, source="direct"),
    }
    edges: list[GraphEdge] = []
    visited: set[str] = {str(root.id)}
    frontier: list[tuple[str, int]] = [(str(root.id), 0)]

    # ── 向上：包含直接母公司（让下级节点图谱保留与上级的关联）──
    if include_parents:
        parent_rels = (await db.execute(
            select(CompanyRelation).where(CompanyRelation.child_company_id == company_id)
        )).scalars().all()
        for rel in parent_rels:
            parent = await db.get(Company, rel.parent_company_id)
            if parent is None or parent.org_id != org_id:
                continue
            pid = str(parent.id)
            edges.append(GraphEdge(
                source=pid, target=str(root.id),
                relation_type=rel.relation_type, holding_ratio=rel.holding_ratio,
            ))
            if pid not in visited:
                visited.add(pid)
                nodes[pid] = GraphNode(
                    id=pid, name=parent.name,
                    holding_ratio=rel.holding_ratio,
                    source="parent", depth=-1,
                )

    # ── 向下：BFS 穿透子公司 ──
    while frontier:
        current_id, current_depth = frontier.pop(0)
        if current_depth >= depth:
            continue
        rels = (await db.execute(
            select(CompanyRelation).where(CompanyRelation.parent_company_id == UUID(current_id))
        )).scalars().all()
        for rel in rels:
            if rel.relation_type == "minority_stake" and not include_minority:
                continue
            if rel.relation_type == "holding" and rel.holding_ratio is not None and rel.holding_ratio < holding_ratio_min:
                continue
            child = await db.get(Company, rel.child_company_id)
            if child is None or child.org_id != org_id:
                continue
            child_id = str(child.id)
            edges.append(GraphEdge(
                source=current_id, target=child_id,
                relation_type=rel.relation_type, holding_ratio=rel.holding_ratio,
            ))
            if child_id not in visited:
                visited.add(child_id)
                nodes[child_id] = GraphNode(
                    id=child_id, name=child.name,
                    holding_ratio=rel.holding_ratio,
                    source="inherited", depth=current_depth + 1,
                )
                frontier.append((child_id, current_depth + 1))

    return CompanyGraphResponse(root_id=str(root.id), nodes=list(nodes.values()), edges=edges)


# ── Risk (A.7) ───────────────────────────────────────────
@router.get("/companies/{company_id}/risk", response_model=CompanyRiskResponse)
async def company_risk(
    company_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> CompanyRiskResponse:
    await _get_owned_company(db, company_id, UUID(user.org_id))
    # All vulns on assets owned by this company.
    vulns = (await db.execute(
        select(Vulnerability)
        .join(Asset, Vulnerability.asset_id == Asset.id)
        .where(Asset.company_id == company_id)
    )).scalars().all()

    # Per-asset risk, then sum.
    asset_ids = {v.asset_id for v in vulns}
    asset_risks: list[float] = []
    for aid in asset_ids:
        asset_vulns = [v for v in vulns if v.asset_id == aid]
        # import lazily to avoid circular at module load
        from src.core.risk import calc_asset_risk
        asset_risks.append(calc_asset_risk(asset_vulns))
    risk_score = calc_company_risk(asset_risks)

    return CompanyRiskResponse(
        company_id=company_id,
        risk_score=risk_score,
        asset_count=len(asset_ids),
        vuln_count=len(vulns),
        by_severity=severity_counts(vulns),
    )


@router.get("/companies/{company_id}/risk/trend", response_model=RiskTrendResponse)
async def company_risk_trend(
    company_id: UUID,
    limit: int = Query(default=30, ge=1, le=200),
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> RiskTrendResponse:
    await _get_owned_company(db, company_id, UUID(user.org_id))
    rows = (await db.execute(
        select(RiskHistory)
        .where(RiskHistory.company_id == company_id)
        .order_by(RiskHistory.snapshot_at.desc())
        .limit(limit)
    )).scalars().all()
    points = [
        RiskTrendPoint(
            snapshot_at=r.snapshot_at, risk_score=r.risk_score,
            asset_count=r.asset_count, vuln_count=r.vuln_count,
        )
        for r in reversed(rows)
    ]
    return RiskTrendResponse(company_id=company_id, points=points)


# ── Detail (聚合视图，消除前端 mock 依赖) ──────────────────
@router.get("/companies/{company_id}/detail", response_model=CompanyDetailResponse)
async def get_company_detail(
    company_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> CompanyDetailResponse:
    org_id = UUID(user.org_id)
    company = await _get_owned_company(db, company_id, org_id)

    # 任务统计
    task_count = (await db.execute(
        select(func.count(Task.id)).where(Task.company_id == company_id)
    )).scalar() or 0
    latest = (await db.execute(
        select(Task.status).where(Task.company_id == company_id).order_by(Task.created_at.desc()).limit(1)
    )).scalar()

    # 下属单位：展开 child_relations 到子公司精简视图
    child_rels = (await db.execute(
        select(CompanyRelation).where(CompanyRelation.parent_company_id == company_id)
    )).scalars().all()
    sub_companies: list[SubCompanyView] = []
    max_depth = 0
    for rel in child_rels:
        child = await db.get(Company, rel.child_company_id)
        if child is None or child.org_id != org_id:
            continue
        sub_companies.append(
            SubCompanyView(
                id=child.id,
                name=child.name,
                full_name=child.name,
                credit_code=child.credit_code,
                industry=child.industry,
                legal_person=child.legal_person,
                business_status=child.business_status,
                website=child.website,
                keywords=child.keywords,
                domains=child.domains,
                work_id_rule=child.work_id_rule,
                holding_ratio=rel.holding_ratio,
                relation_type=rel.relation_type,
                data_source=rel.data_source,
                notes=child.notes,
            )
        )
    # hierarchy_level: 递归计算实际穿透深度（子孙层级）
    async def _calc_depth(parent_id: UUID, seen: set) -> int:
        if parent_id in seen:
            return 0
        seen.add(parent_id)
        children = (await db.execute(
            select(CompanyRelation.child_company_id).where(
                CompanyRelation.parent_company_id == parent_id
            )
        )).scalars().all()
        if not children:
            return 0
        sub_depths = [await _calc_depth(c, seen) for c in children]
        return 1 + max(sub_depths, default=0)

    max_depth = 1 + await _calc_depth(company_id, set())

    # 资产统计
    asset_rows = (await db.execute(
        select(Asset.asset_type, func.count(Asset.id))
        .where(Asset.company_id == company_id)
        .group_by(Asset.asset_type)
    )).all()
    by_type = {r[0] or "unknown": r[1] for r in asset_rows}
    asset_total = sum(by_type.values())

    # 漏洞统计
    vuln_rows = (await db.execute(
        select(Vulnerability.severity, func.count(Vulnerability.id))
        .join(Asset, Vulnerability.asset_id == Asset.id)
        .where(Asset.company_id == company_id)
        .group_by(Vulnerability.severity)
    )).all()
    by_sev = {r[0] or "info": r[1] for r in vuln_rows}
    vuln_total = sum(by_sev.values())

    resp = CompanyDetailResponse(
        **_company_to_response(company, task_count, latest).model_dump(),
        sub_companies=sub_companies,
        sub_company_count=len(sub_companies),
        hierarchy_level=max_depth,
        asset_summary=AssetTypeSummary(total=asset_total, by_type=by_type),
        vuln_summary=VulnSummary(total=vuln_total, by_severity=by_sev),
    )
    return resp


# ── Enrichment (商业 API 采集，A.1 企业关系穿透) ───────────
async def _persist_relations(
    db: AsyncSession,
    parent: Company,
    relations: list,
    org_id: UUID,
    provider: str,
) -> tuple[int, list[Company], list[CompanyRelationResponse]]:
    """落库一组母→子关系到 DB，返回 (新增关系数, 子公司Company列表, 关系响应列表)。"""
    new_rel_count = 0
    created_relations: list[CompanyRelationResponse] = []
    child_companies: list[Company] = []
    for rel in relations:
        child = rel.child
        existing_child = (await db.execute(
            select(Company).where(Company.org_id == org_id, Company.name == child.name).limit(1)
        )).scalar_one_or_none()
        if existing_child is None:
            child_data = {k: v for k, v in child.__dict__.items()
                          if k not in ("name", "provider", "raw") and v not in (None, "", [])}
            existing_child = Company(org_id=org_id, name=child.name, data_source=provider, **child_data)
            db.add(existing_child)
            await db.flush()
        child_companies.append(existing_child)
        existing_rel = (await db.execute(
            select(CompanyRelation).where(
                CompanyRelation.parent_company_id == parent.id,
                CompanyRelation.child_company_id == existing_child.id,
                CompanyRelation.relation_type == rel.relation_type,
            ).limit(1)
        )).scalar_one_or_none()
        if existing_rel is None:
            new_rel = CompanyRelation(
                parent_company_id=parent.id,
                child_company_id=existing_child.id,
                relation_type=rel.relation_type,
                holding_ratio=rel.holding_ratio,
                data_source=provider,
            )
            db.add(new_rel)
            await db.flush()
            new_rel_count += 1
            created_relations.append(CompanyRelationResponse.model_validate(new_rel))
        else:
            created_relations.append(CompanyRelationResponse.model_validate(existing_rel))
    return new_rel_count, child_companies, created_relations


async def _get_or_create_company_by_name(
    db: AsyncSession, name: str, org_id: UUID, provider: str, extra: dict | None = None,
) -> Company:
    """按名称在 org 内查找 Company，不存在则创建。"""
    existing = (await db.execute(
        select(Company).where(Company.org_id == org_id, Company.name == name).limit(1)
    )).scalar_one_or_none()
    if existing is not None:
        return existing
    data = {k: v for k, v in (extra or {}).items()
            if k not in ("name", "provider", "raw") and v not in (None, "", [])}
    co = Company(org_id=org_id, name=name, data_source=provider, **data)
    db.add(co)
    await db.flush()
    return co


async def _do_enrich(
    db: AsyncSession,
    company: Company,
    *,
    provider: str = "yuntu",
    depth: int = 3,
    holding_min: float = 50.0,
    strategy: str = "auto_fill",
    recursive_depth: int = 0,
) -> EnrichmentResponse:
    """核心采集逻辑：调 Provider → 合并 → 落库 → 返回冲突列表。

    云图 level=depth 一次性返回多级关系（子公司+孙公司），investment_path 编码
    完整链路 root——>子——>孙。本方法解析所有层级关系并落库 CompanyRelation。

    被 enrich / batch / create-hook 三处复用。调用方负责事务提交。
    """
    prov: CompanyEnrichmentProvider = get_provider(provider)
    result: EnrichmentResult = await prov.enrich(
        company.name, depth=depth, holding_min=holding_min,
    )

    # 1. 合并主体字段
    plan = plan_company_merge(company, result.root, strategy=strategy)
    apply_merge(company, plan.applied_fields, provider=provider)

    # 2. 落库多级关系：每条 NormalizedRelation 含 parent_name → child
    #    parent 可能是 root（主体）、子公司、或孙公司，按 name 解析 Company。
    org_id = company.org_id
    new_rel_count = 0
    created_relations: list[CompanyRelationResponse] = []
    # 缓存 name → Company，避免重复查询
    name_cache: dict[str, Company] = {company.name: company}

    async def resolve(name: str, extra: dict | None = None) -> Company:
        if name not in name_cache:
            name_cache[name] = await _get_or_create_company_by_name(db, name, org_id, provider, extra)
        return name_cache[name]

    for rel in result.relations:
        parent_co = await resolve(rel.parent_name)
        child_extra = {k: v for k, v in rel.child.__dict__.items()
                       if not k.startswith("_") and k != "_sa_instance_state"}
        child_co = await resolve(rel.child.name, child_extra)
        # 关系去重（唯一约束 parent+child+type）
        existing_rel = (await db.execute(
            select(CompanyRelation).where(
                CompanyRelation.parent_company_id == parent_co.id,
                CompanyRelation.child_company_id == child_co.id,
                CompanyRelation.relation_type == rel.relation_type,
            ).limit(1)
        )).scalar_one_or_none()
        if existing_rel is None:
            new_rel = CompanyRelation(
                parent_company_id=parent_co.id,
                child_company_id=child_co.id,
                relation_type=rel.relation_type,
                holding_ratio=rel.holding_ratio,
                data_source=provider,
            )
            db.add(new_rel)
            await db.flush()
            new_rel_count += 1
            created_relations.append(CompanyRelationResponse.model_validate(new_rel))
        else:
            created_relations.append(CompanyRelationResponse.model_validate(existing_rel))

    await db.commit()
    await db.refresh(company)

    conflicts = [
        FieldConflictItem(
            field=c.field, old_value=c.old_value, new_value=c.new_value,
            old_source=c.old_source, new_source=c.new_source,
        )
        for c in plan.conflicts
    ]
    return EnrichmentResponse(
        company_id=company.id,
        provider=provider,
        fetched_at=result.fetched_at,
        updated_fields=list(plan.applied_fields.keys()),
        new_relations=new_rel_count,
        conflicts=conflicts,
        relations=created_relations,
    )


@router.get("/companies/enrich/providers", response_model=list[str])
async def list_enrich_providers(
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_READ)),
) -> list[str]:
    """列出已注册的采集 provider 名称（供前端下拉）。"""
    return list_providers()


# NOTE: /companies/enrich/batch 是字面路径，必须注册在 /companies/{company_id} 之前，
# 但 FastAPI 对完整路径精确匹配，且本 router 中 /companies/{company_id}/... 子路径
# 均带更深层级，不会与 /companies/enrich/batch 冲突。
@router.post("/companies/enrich/batch", response_model=BatchEnrichResponse)
async def batch_enrich(
    body: BatchEnrichRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_UPDATE)),
    db: AsyncSession = Depends(get_async_db),
) -> BatchEnrichResponse:
    org_id = UUID(user.org_id)
    results: list[BatchEnrichItemResult] = []
    success = failed = total_relations = 0
    for cid in body.company_ids:
        company = await db.get(Company, cid)
        if company is None or company.org_id != org_id:
            results.append(BatchEnrichItemResult(company_id=cid, ok=False, error="Company not found"))
            failed += 1
            continue
        try:
            resp = await _do_enrich(
                db, company, provider=body.provider, depth=body.depth,
                holding_min=body.holding_min, strategy=body.strategy,
            )
            results.append(BatchEnrichItemResult(
                company_id=cid, ok=True,
                new_relations=resp.new_relations, conflicts=len(resp.conflicts),
            ))
            success += 1
            total_relations += resp.new_relations
        except Exception as exc:  # noqa: BLE001
            await db.rollback()
            results.append(BatchEnrichItemResult(company_id=cid, ok=False, error=str(exc)))
            failed += 1
    return BatchEnrichResponse(
        results=results,
        summary={"success": success, "failed": failed, "total_relations": total_relations},
    )


@router.post("/companies/{company_id}/enrich", response_model=EnrichmentResponse)
async def enrich_company(
    company_id: UUID,
    body: EnrichRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_UPDATE)),
    db: AsyncSession = Depends(get_async_db),
) -> EnrichmentResponse:
    company = await _get_owned_company(db, company_id, UUID(user.org_id))
    return await _do_enrich(
        db, company,
        provider=body.provider, depth=body.depth,
        holding_min=body.holding_min, strategy=body.strategy,
        recursive_depth=body.recursive_depth,
    )


@router.post("/companies/{company_id}/enrich/confirm", response_model=EnrichConfirmResponse)
async def confirm_enrich(
    company_id: UUID,
    body: EnrichConfirmRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.COMPANY_UPDATE)),
    db: AsyncSession = Depends(get_async_db),
) -> EnrichConfirmResponse:
    """用户对比冲突字段后，按选择落库（accepted_value 即最终值）。"""
    company = await _get_owned_company(db, company_id, UUID(user.org_id))
    applied: list[str] = []
    for res in body.resolutions:
        if hasattr(company, res.field):
            setattr(company, res.field, res.accepted_value)
            applied.append(res.field)
    company.last_collected_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(company)
    return EnrichConfirmResponse(company_id=company_id, applied_fields=applied)
