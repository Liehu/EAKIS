"""Pydantic schemas for audit log responses."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class Pagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


class AuditLogResponse(BaseModel):
    id: int
    user_id: str | None = None
    username: str | None = None
    org_id: str | None = None
    team_id: str | None = None
    action: str
    resource_type: str
    resource_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    request_method: str | None = None
    request_path: str | None = None
    status_code: int | None = None
    duration_ms: int | None = None
    detail: dict | None = None
    created_at: datetime


class AuditLogListResponse(BaseModel):
    data: list[AuditLogResponse]
    pagination: Pagination
