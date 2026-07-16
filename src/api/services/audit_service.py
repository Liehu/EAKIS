"""Audit log service for centralized audit logging."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from src.models.audit_log import AuditLog


async def write_audit_log(
    db: AsyncSession,
    *,
    user_id: str | None = None,
    username: str | None = None,
    org_id: str | None = None,
    team_id: str | None = None,
    action: str,
    resource_type: str,
    resource_id: str | None = None,
    request: Request | None = None,
    status_code: int = 200,
    duration_ms: int | None = None,
    detail: dict | None = None,
) -> AuditLog:
    """Create an audit log entry."""
    log = AuditLog(
        user_id=user_id,
        username=username,
        org_id=org_id,
        team_id=team_id,
        action=action,
        resource_type=resource_type,
        resource_id=resource_id,
        ip_address=str(request.client.host) if request and request.client else None,
        user_agent=request.headers.get("user-agent") if request else None,
        request_method=request.method if request else None,
        request_path=str(request.url.path) if request else None,
        status_code=status_code,
        duration_ms=duration_ms,
        detail=detail,
    )
    db.add(log)
    return log
