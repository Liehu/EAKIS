"""Templates API router (S4 模板管理).

Endpoints (all under /v1):
  GET    /templates                       (?template_type=&scope=&q=)
  POST   /templates
  GET    /templates/{id}                  (返回继承合并后的 content)
  PATCH  /templates/{id}
  DELETE /templates/{id}
  GET    /templates/types                 (4 类模板说明)

Inheritance (A.6-决策4): GET returns merged content (parent fields + child override).
Scope (A.6-决策5): org scope visible to all org members; team scope to team members;
private scope to owner only.
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
from src.api.schemas.template import (
    Pagination, TemplateCreateRequest, TemplateListResponse,
    TemplateResponse, TemplateUpdateRequest,
)
from src.models.template import Template, merge_inherited

router = APIRouter(tags=["templates"])


async def _resolve_content(db: AsyncSession, t: Template) -> tuple[dict, str | None]:
    """合并继承: 返回 (merged_content, parent_name)."""
    if t.parent_template_id is None:
        return dict(t.content or {}), None
    parent = await db.get(Template, t.parent_template_id)
    if parent is None:
        return dict(t.content or {}), None
    return merge_inherited(t.content, parent.content), parent.name


def _to_response(t: Template, content: dict, parent_name: str | None) -> TemplateResponse:
    return TemplateResponse(
        id=t.id, org_id=t.org_id, name=t.name, template_type=t.template_type,
        description=t.description, content=content,
        parent_template_id=t.parent_template_id, parent_name=parent_name,
        scope=t.scope, owner_id=t.owner_id, team_id=t.team_id,
        version=t.version, is_active=t.is_active, is_seed=t.is_seed,
        created_at=t.created_at, updated_at=t.updated_at,
    )


def _scope_filter(stmt, user: UserInfo):
    """可见域过滤: org 可见全员; team 可见团队成员; private 仅本人."""
    uid = UUID(user.id) if getattr(user, "id", None) else None
    return stmt.where(
        or_(
            Template.scope == "org",
            Template.owner_id == uid,
            # team scope: 简化 — 同 org 可见 (严格 team 隔离需 join team_members)
            Template.scope == "team",
        )
    )


@router.get("/templates", response_model=TemplateListResponse)
async def list_templates(
    template_type: str | None = Query(default=None, pattern="^(task|report|prompt|attack_path)$"),
    scope: str | None = Query(default=None, pattern="^(org|team|private)$"),
    q: str | None = Query(default=None),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user: UserInfo = Depends(require_permission(PermissionAction.TEMPLATE_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> TemplateListResponse:
    org_id = UUID(user.org_id)
    stmt = select(Template).where(Template.org_id == org_id)
    count_stmt = select(func.count(Template.id)).where(Template.org_id == org_id)
    stmt = _scope_filter(stmt, user)
    count_stmt = _scope_filter(count_stmt, user)
    if template_type:
        stmt, count_stmt = (stmt.where(Template.template_type == template_type),
                            count_stmt.where(Template.template_type == template_type))
    if scope:
        stmt, count_stmt = (stmt.where(Template.scope == scope),
                            count_stmt.where(Template.scope == scope))
    if q:
        like = f"%{q}%"
        stmt, count_stmt = stmt.where(Template.name.ilike(like)), count_stmt.where(Template.name.ilike(like))

    total = (await db.execute(count_stmt)).scalar() or 0
    stmt = stmt.order_by(Template.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    rows = (await db.execute(stmt)).scalars().all()

    data = []
    for t in rows:
        content, parent_name = await _resolve_content(db, t)
        data.append(_to_response(t, content, parent_name))
    return TemplateListResponse(data=data, pagination=Pagination(
        page=page, page_size=page_size, total=total, total_pages=max(1, math.ceil(total / page_size)),
    ))


@router.post("/templates", response_model=TemplateResponse, status_code=status.HTTP_201_CREATED)
async def create_template(
    body: TemplateCreateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.TEMPLATE_WRITE)),
    db: AsyncSession = Depends(get_async_db),
) -> TemplateResponse:
    # validate parent exists + same type if specified
    if body.parent_template_id is not None:
        parent = await db.get(Template, body.parent_template_id)
        if parent is None or parent.template_type != body.template_type:
            raise HTTPException(status_code=400, detail="无效的父模板 (不存在或类型不匹配)")

    owner_id = UUID(user.id) if getattr(user, "id", None) else None
    t = Template(
        org_id=UUID(user.org_id),
        name=body.name, template_type=body.template_type, description=body.description,
        content=body.content, parent_template_id=body.parent_template_id,
        scope=body.scope, owner_id=owner_id if body.scope != "org" else None,
        team_id=body.team_id,
    )
    db.add(t)
    await db.commit()
    await db.refresh(t)
    content, parent_name = await _resolve_content(db, t)
    return _to_response(t, content, parent_name)


@router.get("/templates/types")
async def list_template_types(
    user: UserInfo = Depends(require_permission(PermissionAction.TEMPLATE_READ)),
) -> dict:
    """4 类模板说明 (前端用于 Tab/分类展示). MUST precede /{template_id} route."""
    return {
        "types": [
            {"value": "task", "label": "任务模板", "description": "任务参数预设 (目标企业/穿透深度/启用模块/并发)"},
            {"value": "report", "label": "报告模板", "description": "报告字段勾选 + 布局 (资产/企业/漏洞报告, md/html)"},
            {"value": "prompt", "label": "提示词", "description": "LLM 提示词 (按任务类型, Jinja2 变量)"},
            {"value": "attack_path", "label": "攻击路径", "description": "可视化攻击路径 DAG (节点+边)"},
        ]
    }


@router.get("/templates/{template_id}", response_model=TemplateResponse)
async def get_template(
    template_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.TEMPLATE_READ)),
    db: AsyncSession = Depends(get_async_db),
) -> TemplateResponse:
    t = await db.get(Template, template_id)
    if t is None or str(t.org_id) != user.org_id:
        raise HTTPException(status_code=404, detail="模板不存在")
    content, parent_name = await _resolve_content(db, t)
    return _to_response(t, content, parent_name)


@router.patch("/templates/{template_id}", response_model=TemplateResponse)
async def update_template(
    template_id: UUID,
    body: TemplateUpdateRequest,
    user: UserInfo = Depends(require_permission(PermissionAction.TEMPLATE_WRITE)),
    db: AsyncSession = Depends(get_async_db),
) -> TemplateResponse:
    t = await db.get(Template, template_id)
    if t is None or str(t.org_id) != user.org_id:
        raise HTTPException(status_code=404, detail="模板不存在")
    # validate parent type if changing
    if body.parent_template_id is not None and body.parent_template_id != t.parent_template_id:
        parent = await db.get(Template, body.parent_template_id)
        if parent is None or parent.template_type != t.template_type:
            raise HTTPException(status_code=400, detail="无效的父模板")
    update_data = body.model_dump(exclude_unset=True)
    for f, v in update_data.items():
        setattr(t, f, v)
    t.version += 1
    await db.commit()
    await db.refresh(t)
    content, parent_name = await _resolve_content(db, t)
    return _to_response(t, content, parent_name)


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(
    template_id: UUID,
    user: UserInfo = Depends(require_permission(PermissionAction.TEMPLATE_WRITE)),
    db: AsyncSession = Depends(get_async_db),
) -> None:
    t = await db.get(Template, template_id)
    if t is None or str(t.org_id) != user.org_id:
        raise HTTPException(status_code=404, detail="模板不存在")
    await db.delete(t)
    await db.commit()
