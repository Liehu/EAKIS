"""Knowledge base API router (S3).

Endpoints (all under /v1):
  漏洞知识库:
    GET    /knowledge/vulns
    POST   /knowledge/vulns
    GET    /knowledge/vulns/{id}
    PATCH  /knowledge/vulns/{id}
    DELETE /knowledge/vulns/{id}
    POST   /knowledge/vulns/{id}/review        (submit/approve/reject/deprecate)
  Payloads (字典/关键词合并):
    GET    /knowledge/payloads                 (?category=&group_name=&q=)
    POST   /knowledge/payloads
    GET    /knowledge/payloads/{id}
    PATCH  /knowledge/payloads/{id}
    DELETE /knowledge/payloads/{id}
    POST   /knowledge/payloads/{id}/hit        (hit_count += 1)
  指纹库:
    GET    /knowledge/fingerprints
    POST   /knowledge/fingerprints
    GET    /knowledge/fingerprints/{id}
    PATCH  /knowledge/fingerprints/{id}
    DELETE /knowledge/fingerprints/{id}
  数据源:
    GET    /knowledge/datasources
    POST   /knowledge/datasources
    PATCH  /knowledge/datasources/{id}
    DELETE /knowledge/datasources/{id}
  攻防手册:
    GET    /knowledge/handbooks
    POST   /knowledge/handbooks
    GET    /knowledge/handbooks/{id}
    PATCH  /knowledge/handbooks/{id}
    DELETE /knowledge/handbooks/{id}
"""

from __future__ import annotations

import math
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import UserInfo
from src.api.dependencies import get_async_db
from src.api.deps.permissions import PermissionAction, require_permission
from src.api.schemas.knowledge import (
    DatasourceCreateRequest,
    DatasourceListResponse,
    DatasourceResponse,
    FingerprintCreateRequest,
    FingerprintListResponse,
    FingerprintResponse,
    HandbookCreateRequest,
    HandbookListResponse,
    HandbookResponse,
    Pagination,
    PayloadCreateRequest,
    PayloadListResponse,
    PayloadResponse,
    PayloadUpdateRequest,
    ReviewRequest,
    VulnKnowledgeCreateRequest,
    VulnKnowledgeListResponse,
    VulnKnowledgeResponse,
    VulnKnowledgeUpdateRequest,
)
from src.models.knowledge import (
    Fingerprint,
    KnowledgeDatasource,
    KnowledgeHandbook,
    KnowledgeTag,
    Payload,
    VulnKnowledge,
)

router = APIRouter(tags=["knowledge"])


# ── helpers ──────────────────────────────────────────────
async def _load_tags(db: AsyncSession, table, owner_col, owner_id) -> list[str]:
    """Load tag names for a knowledge item."""
    rows = (await db.execute(
        select(KnowledgeTag.tag).where(owner_col == owner_id)
    )).scalars().all()
    return list(rows)


def _paginate(page: int, page_size: int, total: int) -> Pagination:
    return Pagination(page=page, page_size=page_size, total=total, total_pages=max(1, math.ceil(total / page_size)))


# ── 漏洞知识库 ────────────────────────────────────────────
@router.get("/knowledge/vulns", response_model=VulnKnowledgeListResponse)
async def list_vulns(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    severity: str | None = Query(default=None),
    status_: str | None = Query(default=None, alias="status"),
    vuln_type: str | None = Query(default=None),
    q: str | None = Query(default=None, description="名称/编号/厂商模糊"),
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> VulnKnowledgeListResponse:
    stmt = select(VulnKnowledge)
    count_stmt = select(func.count(VulnKnowledge.id))
    if severity:
        stmt, count_stmt = (stmt.where(VulnKnowledge.severity == severity),
                            count_stmt.where(VulnKnowledge.severity == severity))
    if status_:
        stmt, count_stmt = (stmt.where(VulnKnowledge.status == status_),
                            count_stmt.where(VulnKnowledge.status == status_))
    if vuln_type:
        stmt, count_stmt = (stmt.where(VulnKnowledge.vuln_type == vuln_type),
                            count_stmt.where(VulnKnowledge.vuln_type == vuln_type))
    if q:
        like = f"%{q}%"
        cond = or_(VulnKnowledge.name.ilike(like), VulnKnowledge.vuln_id.ilike(like), VulnKnowledge.vendor.ilike(like))
        stmt, count_stmt = stmt.where(cond), count_stmt.where(cond)

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(VulnKnowledge.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    data = []
    for v in rows:
        tags = await _load_tags(db, KnowledgeTag, KnowledgeTag.vuln_id, v.id)
        data.append(VulnKnowledgeResponse(**{c.name: getattr(v, c.name) for c in v.__table__.columns}, tags=tags))
    return VulnKnowledgeListResponse(data=data, pagination=_paginate(page, page_size, total))


@router.post("/knowledge/vulns", response_model=VulnKnowledgeResponse, status_code=status.HTTP_201_CREATED)
async def create_vuln(
    body: VulnKnowledgeCreateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_WRITE)),
    db: AsyncSession = Depends(get_async_db),
) -> VulnKnowledgeResponse:
    vuln = VulnKnowledge(**body.model_dump(), contributed_by=user.email, status="draft")
    db.add(vuln)
    await db.commit()
    await db.refresh(vuln)
    return VulnKnowledgeResponse(**{c.name: getattr(vuln, c.name) for c in vuln.__table__.columns}, tags=[])


@router.get("/knowledge/vulns/{vuln_id}", response_model=VulnKnowledgeResponse)
async def get_vuln(
    vuln_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> VulnKnowledgeResponse:
    v = await db.get(VulnKnowledge, vuln_id)
    if v is None:
        raise HTTPException(status_code=404, detail="漏洞知识不存在")
    tags = await _load_tags(db, KnowledgeTag, KnowledgeTag.vuln_id, v.id)
    return VulnKnowledgeResponse(**{c.name: getattr(v, c.name) for c in v.__table__.columns}, tags=tags)


@router.patch("/knowledge/vulns/{vuln_id}", response_model=VulnKnowledgeResponse)
async def update_vuln(
    vuln_id: UUID,
    body: VulnKnowledgeUpdateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_WRITE)),
    db: AsyncSession = Depends(get_async_db),
) -> VulnKnowledgeResponse:
    v = await db.get(VulnKnowledge, vuln_id)
    if v is None:
        raise HTTPException(status_code=404, detail="漏洞知识不存在")
    for f, val in body.model_dump(exclude_unset=True).items():
        setattr(v, f, val)
    await db.commit()
    await db.refresh(v)
    tags = await _load_tags(db, KnowledgeTag, KnowledgeTag.vuln_id, v.id)
    return VulnKnowledgeResponse(**{c.name: getattr(v, c.name) for c in v.__table__.columns}, tags=tags)


@router.delete("/knowledge/vulns/{vuln_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vuln(
    vuln_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    v = await db.get(VulnKnowledge, vuln_id)
    if v is None:
        raise HTTPException(status_code=404, detail="漏洞知识不存在")
    await db.delete(v)
    await db.commit()


@router.post("/knowledge/vulns/{vuln_id}/review", response_model=VulnKnowledgeResponse)
async def review_vuln(
    vuln_id: UUID,
    body: ReviewRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> VulnKnowledgeResponse:
    """审核状态机: draft→(submit)→pending_review→(approve)→published / (reject)→draft;
    published→(deprecate)→deprecated."""
    v = await db.get(VulnKnowledge, vuln_id)
    if v is None:
        raise HTTPException(status_code=404, detail="漏洞知识不存在")
    transitions = {
        "submit": (["draft"], "pending_review"),
        "approve": (["pending_review"], "published"),
        "reject": (["pending_review"], "draft"),
        "deprecate": (["published"], "deprecated"),
    }
    allowed_from, target = transitions[body.action]
    if v.status not in allowed_from:
        raise HTTPException(status_code=400, detail=f"不能从 {v.status} 执行 {body.action}")
    v.status = target
    v.reviewed_by = user.email
    if body.review_comment is not None:
        v.review_comment = body.review_comment
    await db.commit()
    await db.refresh(v)
    tags = await _load_tags(db, KnowledgeTag, KnowledgeTag.vuln_id, v.id)
    return VulnKnowledgeResponse(**{c.name: getattr(v, c.name) for c in v.__table__.columns}, tags=tags)


# ── Payloads (字典/关键词合并) ────────────────────────────
@router.get("/knowledge/payloads", response_model=PayloadListResponse)
async def list_payloads(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = Query(default=None, description="pass/path/user/header/payload/keywords"),
    group_name: str | None = Query(default=None),
    q: str | None = Query(default=None, description="name/content 包含"),
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> PayloadListResponse:
    stmt = select(Payload)
    count_stmt = select(func.count(Payload.id))
    if category:
        stmt, count_stmt = stmt.where(Payload.category == category), count_stmt.where(Payload.category == category)
    if group_name:
        stmt, count_stmt = stmt.where(Payload.group_name == group_name), count_stmt.where(Payload.group_name == group_name)
    if q:
        like = f"%{q}%"
        cond = or_(Payload.name.ilike(like), Payload.content.ilike(like))
        stmt, count_stmt = stmt.where(cond), count_stmt.where(cond)

    total = (await db.execute(count_stmt)).scalar() or 0
    # 默认按权重降序 (weight 高优先)
    stmt = stmt.order_by(Payload.weight.desc(), Payload.hit_count.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    data = []
    for p in rows:
        tags = await _load_tags(db, KnowledgeTag, KnowledgeTag.payload_id, p.id)
        data.append(PayloadResponse(**{c.name: getattr(p, c.name) for c in p.__table__.columns}, tags=tags))
    return PayloadListResponse(data=data, pagination=_paginate(page, page_size, total))


@router.post("/knowledge/payloads", response_model=PayloadResponse, status_code=status.HTTP_201_CREATED)
async def create_payload(
    body: PayloadCreateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_WRITE)),
    db: AsyncSession = Depends(get_async_db),
) -> PayloadResponse:
    p = Payload(**body.model_dump())
    db.add(p)
    await db.commit()
    await db.refresh(p)
    return PayloadResponse(**{c.name: getattr(p, c.name) for c in p.__table__.columns}, tags=[])


@router.get("/knowledge/payloads/{payload_id}", response_model=PayloadResponse)
async def get_payload(
    payload_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> PayloadResponse:
    p = await db.get(Payload, payload_id)
    if p is None:
        raise HTTPException(status_code=404, detail="字典项不存在")
    tags = await _load_tags(db, KnowledgeTag, KnowledgeTag.payload_id, p.id)
    return PayloadResponse(**{c.name: getattr(p, c.name) for c in p.__table__.columns}, tags=tags)


@router.patch("/knowledge/payloads/{payload_id}", response_model=PayloadResponse)
async def update_payload(
    payload_id: UUID,
    body: PayloadUpdateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_WRITE)),
    db: AsyncSession = Depends(get_async_db),
) -> PayloadResponse:
    p = await db.get(Payload, payload_id)
    if p is None:
        raise HTTPException(status_code=404, detail="字典项不存在")
    for f, val in body.model_dump(exclude_unset=True).items():
        setattr(p, f, val)
    await db.commit()
    await db.refresh(p)
    tags = await _load_tags(db, KnowledgeTag, KnowledgeTag.payload_id, p.id)
    return PayloadResponse(**{c.name: getattr(p, c.name) for c in p.__table__.columns}, tags=tags)


@router.delete("/knowledge/payloads/{payload_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_payload(
    payload_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    p = await db.get(Payload, payload_id)
    if p is None:
        raise HTTPException(status_code=404, detail="字典项不存在")
    await db.delete(p)
    await db.commit()


@router.post("/knowledge/payloads/{payload_id}/hit", response_model=PayloadResponse)
async def record_payload_hit(
    payload_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_WRITE)),
    db: AsyncSession = Depends(get_async_db),
) -> PayloadResponse:
    """记录一次命中: hit_count += 1 (A.4 字典命中统计)."""
    p = await db.get(Payload, payload_id)
    if p is None:
        raise HTTPException(status_code=404, detail="字典项不存在")
    p.hit_count = (p.hit_count or 0) + 1
    await db.commit()
    await db.refresh(p)
    return PayloadResponse(**{c.name: getattr(p, c.name) for c in p.__table__.columns}, tags=[])


# ── 指纹库 ────────────────────────────────────────────────
@router.get("/knowledge/fingerprints", response_model=FingerprintListResponse)
async def list_fingerprints(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = Query(default=None),
    component: str | None = Query(default=None),
    q: str | None = Query(default=None),
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> FingerprintListResponse:
    stmt = select(Fingerprint)
    count_stmt = select(func.count(Fingerprint.id))
    if category:
        stmt, count_stmt = stmt.where(Fingerprint.category == category), count_stmt.where(Fingerprint.category == category)
    if component:
        stmt, count_stmt = stmt.where(Fingerprint.component == component), count_stmt.where(Fingerprint.component == component)
    if q:
        like = f"%{q}%"
        cond = or_(Fingerprint.name.ilike(like), Fingerprint.component.ilike(like))
        stmt, count_stmt = stmt.where(cond), count_stmt.where(cond)
    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(Fingerprint.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    data = []
    for f in rows:
        tags = await _load_tags(db, KnowledgeTag, KnowledgeTag.fingerprint_id, f.id)
        vuln_count = (await db.execute(
            select(func.count(VulnKnowledge.id)).where(VulnKnowledge.fingerprint_id == f.id)
        )).scalar() or 0
        data.append(FingerprintResponse(
            id=f.id, name=f.name, category=f.category, component=f.component, version=f.version,
            match_type=f.match_type, match_rule=f.match_rule, description=f.description,
            status=f.status, contributed_by=f.contributed_by, reviewed_by=f.reviewed_by,
            tags=tags, vuln_count=vuln_count, created_at=f.created_at, updated_at=f.updated_at,
        ))
    return FingerprintListResponse(data=data, pagination=_paginate(page, page_size, total))


@router.post("/knowledge/fingerprints", response_model=FingerprintResponse, status_code=status.HTTP_201_CREATED)
async def create_fingerprint(
    body: FingerprintCreateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_WRITE)),
    db: AsyncSession = Depends(get_async_db),
) -> FingerprintResponse:
    f = Fingerprint(**body.model_dump(), contributed_by=user.email, status="draft")
    db.add(f)
    await db.commit()
    await db.refresh(f)
    return FingerprintResponse(
        id=f.id, name=f.name, category=f.category, component=f.component, version=f.version,
        match_type=f.match_type, match_rule=f.match_rule, description=f.description,
        status=f.status, contributed_by=f.contributed_by, reviewed_by=f.reviewed_by,
        tags=[], vuln_count=0, created_at=f.created_at, updated_at=f.updated_at,
    )


@router.get("/knowledge/fingerprints/{fp_id}", response_model=FingerprintResponse)
async def get_fingerprint(
    fp_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> FingerprintResponse:
    f = await db.get(Fingerprint, fp_id)
    if f is None:
        raise HTTPException(status_code=404, detail="指纹不存在")
    tags = await _load_tags(db, KnowledgeTag, KnowledgeTag.fingerprint_id, f.id)
    vuln_count = (await db.execute(
        select(func.count(VulnKnowledge.id)).where(VulnKnowledge.fingerprint_id == f.id)
    )).scalar() or 0
    return FingerprintResponse(
        id=f.id, name=f.name, category=f.category, component=f.component, version=f.version,
        match_type=f.match_type, match_rule=f.match_rule, description=f.description,
        status=f.status, contributed_by=f.contributed_by, reviewed_by=f.reviewed_by,
        tags=tags, vuln_count=vuln_count, created_at=f.created_at, updated_at=f.updated_at,
    )


@router.patch("/knowledge/fingerprints/{fp_id}", response_model=FingerprintResponse)
async def update_fingerprint(
    fp_id: UUID,
    body: FingerprintCreateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_WRITE)),
    db: AsyncSession = Depends(get_async_db),
) -> FingerprintResponse:
    f = await db.get(Fingerprint, fp_id)
    if f is None:
        raise HTTPException(status_code=404, detail="指纹不存在")
    for field, val in body.model_dump(exclude_unset=True).items():
        setattr(f, field, val)
    await db.commit()
    await db.refresh(f)
    tags = await _load_tags(db, KnowledgeTag, KnowledgeTag.fingerprint_id, f.id)
    vuln_count = (await db.execute(
        select(func.count(VulnKnowledge.id)).where(VulnKnowledge.fingerprint_id == f.id)
    )).scalar() or 0
    return FingerprintResponse(
        id=f.id, name=f.name, category=f.category, component=f.component, version=f.version,
        match_type=f.match_type, match_rule=f.match_rule, description=f.description,
        status=f.status, contributed_by=f.contributed_by, reviewed_by=f.reviewed_by,
        tags=tags, vuln_count=vuln_count, created_at=f.created_at, updated_at=f.updated_at,
    )


@router.delete("/knowledge/fingerprints/{fp_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_fingerprint(
    fp_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    f = await db.get(Fingerprint, fp_id)
    if f is None:
        raise HTTPException(status_code=404, detail="指纹不存在")
    await db.delete(f)
    await db.commit()


# ── 数据源 ────────────────────────────────────────────────
@router.get("/knowledge/datasources", response_model=DatasourceListResponse)
async def list_datasources(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    platform: str | None = Query(default=None),
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> DatasourceListResponse:
    stmt = select(KnowledgeDatasource)
    count_stmt = select(func.count(KnowledgeDatasource.id))
    if platform:
        stmt, count_stmt = stmt.where(KnowledgeDatasource.platform == platform), count_stmt.where(KnowledgeDatasource.platform == platform)
    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(KnowledgeDatasource.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    data = []
    for d in rows:
        tags = await _load_tags(db, KnowledgeTag, KnowledgeTag.datasource_id, d.id)
        data.append(DatasourceResponse(**{c.name: getattr(d, c.name) for c in d.__table__.columns}, tags=tags))
    return DatasourceListResponse(data=data, pagination=_paginate(page, page_size, total))


@router.post("/knowledge/datasources", response_model=DatasourceResponse, status_code=status.HTTP_201_CREATED)
async def create_datasource(
    body: DatasourceCreateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_WRITE)),
    db: AsyncSession = Depends(get_async_db),
) -> DatasourceResponse:
    d = KnowledgeDatasource(**body.model_dump())
    db.add(d)
    await db.commit()
    await db.refresh(d)
    return DatasourceResponse(**{c.name: getattr(d, c.name) for c in d.__table__.columns}, tags=[])


@router.patch("/knowledge/datasources/{ds_id}", response_model=DatasourceResponse)
async def update_datasource(
    ds_id: UUID,
    body: DatasourceCreateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_WRITE)),
    db: AsyncSession = Depends(get_async_db),
) -> DatasourceResponse:
    d = await db.get(KnowledgeDatasource, ds_id)
    if d is None:
        raise HTTPException(status_code=404, detail="数据源不存在")
    for f, val in body.model_dump(exclude_unset=True).items():
        setattr(d, f, val)
    await db.commit()
    await db.refresh(d)
    tags = await _load_tags(db, KnowledgeTag, KnowledgeTag.datasource_id, d.id)
    return DatasourceResponse(**{c.name: getattr(d, c.name) for c in d.__table__.columns}, tags=tags)


@router.delete("/knowledge/datasources/{ds_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_datasource(
    ds_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    d = await db.get(KnowledgeDatasource, ds_id)
    if d is None:
        raise HTTPException(status_code=404, detail="数据源不存在")
    await db.delete(d)
    await db.commit()


# ── 攻防手册 ──────────────────────────────────────────────
@router.get("/knowledge/handbooks", response_model=HandbookListResponse)
async def list_handbooks(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    category: str | None = Query(default=None),
    q: str | None = Query(default=None),
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> HandbookListResponse:
    stmt = select(KnowledgeHandbook)
    count_stmt = select(func.count(KnowledgeHandbook.id))
    if category:
        stmt, count_stmt = stmt.where(KnowledgeHandbook.category == category), count_stmt.where(KnowledgeHandbook.category == category)
    if q:
        like = f"%{q}%"
        cond = or_(KnowledgeHandbook.title.ilike(like), KnowledgeHandbook.content.ilike(like))
        stmt, count_stmt = stmt.where(cond), count_stmt.where(cond)
    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(KnowledgeHandbook.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()
    data = []
    for h in rows:
        tags = await _load_tags(db, KnowledgeTag, KnowledgeTag.handbook_id, h.id)
        data.append(HandbookResponse(**{c.name: getattr(h, c.name) for c in h.__table__.columns}, tags=tags))
    return HandbookListResponse(data=data, pagination=_paginate(page, page_size, total))


@router.post("/knowledge/handbooks", response_model=HandbookResponse, status_code=status.HTTP_201_CREATED)
async def create_handbook(
    body: HandbookCreateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_WRITE)),
    db: AsyncSession = Depends(get_async_db),
) -> HandbookResponse:
    h = KnowledgeHandbook(**body.model_dump(), contributed_by=user.email, status="draft")
    db.add(h)
    await db.commit()
    await db.refresh(h)
    return HandbookResponse(**{c.name: getattr(h, c.name) for c in h.__table__.columns}, tags=[])


@router.get("/knowledge/handbooks/{hb_id}", response_model=HandbookResponse)
async def get_handbook(
    hb_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> HandbookResponse:
    h = await db.get(KnowledgeHandbook, hb_id)
    if h is None:
        raise HTTPException(status_code=404, detail="手册不存在")
    tags = await _load_tags(db, KnowledgeTag, KnowledgeTag.handbook_id, h.id)
    return HandbookResponse(**{c.name: getattr(h, c.name) for c in h.__table__.columns}, tags=tags)


@router.patch("/knowledge/handbooks/{hb_id}", response_model=HandbookResponse)
async def update_handbook(
    hb_id: UUID,
    body: HandbookCreateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_WRITE)),
    db: AsyncSession = Depends(get_async_db),
) -> HandbookResponse:
    h = await db.get(KnowledgeHandbook, hb_id)
    if h is None:
        raise HTTPException(status_code=404, detail="手册不存在")
    for f, val in body.model_dump(exclude_unset=True).items():
        setattr(h, f, val)
    await db.commit()
    await db.refresh(h)
    tags = await _load_tags(db, KnowledgeTag, KnowledgeTag.handbook_id, h.id)
    return HandbookResponse(**{c.name: getattr(h, c.name) for c in h.__table__.columns}, tags=tags)


@router.delete("/knowledge/handbooks/{hb_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_handbook(
    hb_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.KNOWLEDGE_ADMIN)),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    h = await db.get(KnowledgeHandbook, hb_id)
    if h is None:
        raise HTTPException(status_code=404, detail="手册不存在")
    await db.delete(h)
    await db.commit()
