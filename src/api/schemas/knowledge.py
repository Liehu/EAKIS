"""Pydantic schemas for knowledge base endpoints (S3)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Pagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


# ── 漏洞知识库 ────────────────────────────────────────────
class VulnKnowledgeCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    severity: str = Field(..., pattern="^(critical|high|medium|low|info)$")
    vuln_id: str | None = Field(default=None, max_length=100)
    vuln_type: str | None = None
    vendor: str | None = None
    product: str | None = None
    version_range: str | None = None
    affected_scope: str | None = None
    fingerprint_id: UUID | None = None
    poc: str | None = None
    remediation: str | None = None
    data_source: str | None = None
    upstream_ref: str | None = None


class VulnKnowledgeUpdateRequest(BaseModel):
    name: str | None = None
    severity: str | None = Field(default=None, pattern="^(critical|high|medium|low|info)$")
    vuln_id: str | None = None
    vuln_type: str | None = None
    vendor: str | None = None
    product: str | None = None
    version_range: str | None = None
    affected_scope: str | None = None
    fingerprint_id: UUID | None = None
    poc: str | None = None
    remediation: str | None = None


class ReviewRequest(BaseModel):
    """审核动作: submit(提交审核) / approve(通过) / reject(驳回) / deprecate(弃用)."""
    action: str = Field(..., pattern="^(submit|approve|reject|deprecate)$")
    review_comment: str | None = None


class VulnKnowledgeResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    severity: str
    vuln_id: str | None = None
    vuln_type: str | None = None
    vendor: str | None = None
    product: str | None = None
    version_range: str | None = None
    affected_scope: str | None = None
    fingerprint_id: UUID | None = None
    poc: str | None = None
    remediation: str | None = None
    data_source: str | None = None
    upstream_ref: str | None = None
    status: str
    contributed_by: str | None = None
    reviewed_by: str | None = None
    review_comment: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class VulnKnowledgeListResponse(BaseModel):
    data: list[VulnKnowledgeResponse]
    pagination: Pagination


# ── Payloads (合并 字典/关键词) ───────────────────────────
class PayloadCreateRequest(BaseModel):
    name: str | None = None
    content: str = Field(..., min_length=1)
    category: str = Field(..., pattern="^(pass|path|user|header|payload|keywords)$")
    group_name: str | None = None
    weight: float = Field(default=1.0, ge=0)
    description: str | None = None
    data_source: str | None = None


class PayloadUpdateRequest(BaseModel):
    name: str | None = None
    content: str | None = None
    category: str | None = Field(default=None, pattern="^(pass|path|user|header|payload|keywords)$")
    group_name: str | None = None
    weight: float | None = Field(default=None, ge=0)
    description: str | None = None


class PayloadResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str | None = None
    content: str
    category: str
    group_name: str | None = None
    weight: float
    hit_count: int
    description: str | None = None
    data_source: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class PayloadListResponse(BaseModel):
    data: list[PayloadResponse]
    pagination: Pagination


# ── 指纹库 ────────────────────────────────────────────────
class FingerprintCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    category: str | None = None
    component: str | None = None
    version: str | None = None
    match_type: str | None = None
    match_rule: str = Field(..., min_length=1)
    description: str | None = None
    data_source: str | None = None


class FingerprintResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    category: str | None = None
    component: str | None = None
    version: str | None = None
    match_type: str | None = None
    match_rule: str
    description: str | None = None
    status: str
    contributed_by: str | None = None
    reviewed_by: str | None = None
    tags: list[str] = Field(default_factory=list)
    vuln_count: int = 0
    created_at: datetime
    updated_at: datetime


class FingerprintListResponse(BaseModel):
    data: list[FingerprintResponse]
    pagination: Pagination


# ── 数据源 ────────────────────────────────────────────────
class DatasourceCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    platform: str = Field(..., min_length=1, max_length=50)
    api_base_url: str | None = None
    config: str | None = None
    description: str | None = None


class DatasourceResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    name: str
    platform: str
    api_base_url: str | None = None
    config: str | None = None
    description: str | None = None
    is_active: int
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class DatasourceListResponse(BaseModel):
    data: list[DatasourceResponse]
    pagination: Pagination


# ── 攻防手册 ──────────────────────────────────────────────
class HandbookCreateRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=300)
    category: str | None = None
    content: str = Field(..., min_length=1)
    summary: str | None = None


class HandbookResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    title: str
    category: str | None = None
    content: str
    summary: str | None = None
    status: str
    contributed_by: str | None = None
    reviewed_by: str | None = None
    tags: list[str] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class HandbookListResponse(BaseModel):
    data: list[HandbookResponse]
    pagination: Pagination
