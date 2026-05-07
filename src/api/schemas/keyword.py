"""Pydantic schemas for keyword API endpoints (section 9.3)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# --- Response schemas ---

class KeywordItem(BaseModel):
    id: UUID
    word: str
    type: str
    weight: float
    confidence: float
    source: str | None = None
    derived: bool = False
    used_in_dsl: bool = False

    model_config = {"from_attributes": True}


class KeywordSummary(BaseModel):
    business_count: int = 0
    tech_count: int = 0
    entity_count: int = 0
    total: int = 0


class Pagination(BaseModel):
    page: int = 1
    page_size: int = 20
    total: int = 0
    total_pages: int = 0


class KeywordListResponse(BaseModel):
    data: list[KeywordItem] = Field(default_factory=list)
    summary: KeywordSummary = Field(default_factory=KeywordSummary)
    pagination: Pagination = Field(default_factory=Pagination)


class KeywordDetailResponse(BaseModel):
    id: UUID
    word: str
    type: str
    weight: float
    confidence: float
    source: str | None = None
    derived: bool = False
    used_in_dsl: bool = False
    created_at: datetime | None = None

    model_config = {"from_attributes": True}


# --- Request schemas ---

class KeywordCreateRequest(BaseModel):
    word: str = Field(..., min_length=1, max_length=200)
    type: str = Field(..., pattern=r"^(business|tech|entity)$")
    weight: float = Field(default=0.5, ge=0.0, le=1.0)
    reason: str | None = None


class KeywordUpdateRequest(BaseModel):
    weight: float | None = Field(default=None, ge=0.0, le=1.0)
    used_in_dsl: bool | None = None
