"""Pydantic schemas for team management requests/responses."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Pagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


# --- Request schemas ---

class TeamCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: str | None = None


class TeamUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None


class TeamMemberAddRequest(BaseModel):
    user_id: UUID
    role_name: str = Field(default="engineer", pattern="^(super_admin|org_admin|team_lead|engineer|analyst|auditor)$")


class TeamMemberUpdateRequest(BaseModel):
    role_name: str = Field(..., pattern="^(super_admin|org_admin|team_lead|engineer|analyst|auditor)$")


# --- Response schemas ---

class TeamMemberResponse(BaseModel):
    user_id: UUID
    team_id: UUID
    role_name: str
    display_name: str
    email: str
    joined_at: datetime
    invited_by: UUID | None = None


class TeamResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    name: str
    description: str | None = None
    created_at: datetime
    updated_at: datetime
    member_count: int = 0


class TeamDetailResponse(TeamResponse):
    members: list[TeamMemberResponse] = []


class TeamListResponse(BaseModel):
    data: list[TeamResponse]
    pagination: Pagination
