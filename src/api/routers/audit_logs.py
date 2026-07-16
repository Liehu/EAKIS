"""Audit log API endpoints (admin)."""

from __future__ import annotations

import math
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.auth import UserInfo
from src.api.dependencies import get_async_db
from src.api.deps.permissions import PermissionAction, require_permission
from src.api.schemas.audit_log import AuditLogListResponse, AuditLogResponse, Pagination
from src.models.audit_log import AuditLog

router = APIRouter(tags=["admin-audit"])


@router.get("/admin/audit-logs", response_model=AuditLogListResponse)
async def list_audit_logs(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    user_id: str | None = Query(default=None),
    action: str | None = Query(default=None),
    resource_type: str | None = Query(default=None),
    start_date: datetime | None = Query(default=None),
    end_date: datetime | None = Query(default=None),
    user: UserInfo = Depends(require_permission(PermissionAction.SYSTEM_AUDIT)),
    db: AsyncSession = Depends(get_async_db),
) -> AuditLogListResponse:
    """List audit logs with filters."""
    stmt = select(AuditLog)
    count_stmt = select(func.count(AuditLog.id))

    if user_id:
        stmt = stmt.where(AuditLog.user_id == user_id)
        count_stmt = count_stmt.where(AuditLog.user_id == user_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
        count_stmt = count_stmt.where(AuditLog.action == action)
    if resource_type:
        stmt = stmt.where(AuditLog.resource_type == resource_type)
        count_stmt = count_stmt.where(AuditLog.resource_type == resource_type)
    if start_date:
        stmt = stmt.where(AuditLog.created_at >= start_date)
        count_stmt = count_stmt.where(AuditLog.created_at >= start_date)
    if end_date:
        stmt = stmt.where(AuditLog.created_at <= end_date)
        count_stmt = count_stmt.where(AuditLog.created_at <= end_date)

    total = (await db.execute(count_stmt)).scalar() or 0
    total_pages = max(1, math.ceil(total / page_size))

    stmt = stmt.order_by(AuditLog.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(stmt)
    logs = result.scalars().all()

    return AuditLogListResponse(
        data=[_to_response(log) for log in logs],
        pagination=Pagination(page=page, page_size=page_size, total=total, total_pages=total_pages),
    )


@router.get("/admin/audit-logs/{log_id}", response_model=AuditLogResponse)
async def get_audit_log(
    log_id: int,
    user: UserInfo = Depends(require_permission(PermissionAction.SYSTEM_AUDIT)),
    db: AsyncSession = Depends(get_async_db),
) -> AuditLogResponse:
    """Get a single audit log detail."""
    log = await db.get(AuditLog, log_id)
    if log is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Audit log not found")
    return _to_response(log)


def _to_response(log: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=log.id,
        user_id=str(log.user_id) if log.user_id else None,
        username=log.username,
        org_id=str(log.org_id) if log.org_id else None,
        team_id=str(log.team_id) if log.team_id else None,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=log.resource_id,
        ip_address=str(log.ip_address) if log.ip_address else None,
        user_agent=log.user_agent,
        request_method=log.request_method,
        request_path=log.request_path,
        status_code=log.status_code,
        duration_ms=log.duration_ms,
        detail=log.detail,
        created_at=log.created_at,
    )
