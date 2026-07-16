"""Pydantic schemas for template endpoints (S4)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Pagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


# ── 统一模板 ──────────────────────────────────────────────
class TemplateCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    template_type: str = Field(..., pattern="^(task|report|prompt|attack_path)$")
    description: str | None = None
    content: dict = Field(default_factory=dict)
    parent_template_id: UUID | None = None
    scope: str = Field(default="org", pattern="^(org|team|private)$")
    team_id: UUID | None = None


class TemplateUpdateRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    content: dict | None = None
    parent_template_id: UUID | None = None
    scope: str | None = Field(default=None, pattern="^(org|team|private)$")
    team_id: UUID | None = None
    is_active: int | None = None


class TemplateResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    name: str
    template_type: str
    description: str | None = None
    content: dict
    parent_template_id: UUID | None = None
    parent_name: str | None = None
    scope: str
    owner_id: UUID | None = None
    team_id: UUID | None = None
    version: int
    is_active: int
    is_seed: int
    created_at: datetime
    updated_at: datetime


class TemplateListResponse(BaseModel):
    data: list[TemplateResponse]
    pagination: Pagination
