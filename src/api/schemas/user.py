"""Pydantic schemas for user and auth related requests/responses."""

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

class UserCreateRequest(BaseModel):
    email: str = Field(..., min_length=1, max_length=300)
    password: str = Field(..., min_length=8, max_length=128)
    display_name: str = Field(..., min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    role_name: str = Field(default="engineer", pattern="^(super_admin|org_admin|team_lead|engineer|analyst|auditor)$")
    team_ids: list[UUID] | None = Field(default=None)


class UserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=100)
    phone: str | None = Field(default=None, max_length=50)
    avatar_url: str | None = Field(default=None, max_length=500)
    is_active: bool | None = None


class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8, max_length=128)


class RefreshTokenRequest(BaseModel):
    refresh_token: str = Field(..., min_length=1)


# --- Response schemas ---

class UserResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    email: str
    display_name: str
    phone: str | None = None
    avatar_url: str | None = None
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime


class UserListResponse(BaseModel):
    data: list[UserResponse]
    pagination: Pagination


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshTokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class MeResponse(BaseModel):
    id: UUID
    org_id: UUID
    email: str
    display_name: str
    phone: str | None = None
    avatar_url: str | None = None
    is_active: bool
    last_login_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    role: str
    permissions: list[str]
    teams: dict[str, dict[str, str]]
