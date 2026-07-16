"""Pydantic schemas for company endpoints (A.1 企业关系穿透)."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Pagination(BaseModel):
    page: int
    page_size: int
    total: int
    total_pages: int


# ── Company ──────────────────────────────────────────────
class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=300)
    aliases: list[str] | None = None
    credit_code: str | None = Field(default=None, max_length=64)
    industry: str | None = Field(default=None, max_length=100)
    registered_capital: str | None = None
    established_at: datetime | None = None
    legal_person: str | None = None
    business_status: str | None = None
    website: str | None = None
    logo_url: str | None = None
    # business (editable)
    email_domains: list[str] | None = None
    work_id_rule: str | None = None
    keywords: list[str] | None = None
    domains: list[str] | None = None
    ip_ranges: list[str] | None = None
    notes: str | None = None


class CompanyCreateRequest(CompanyBase):
    org_id: UUID | None = None  # defaults to caller's org


class CompanyUpdateRequest(BaseModel):
    # Only business fields + collected fields are mutable.
    aliases: list[str] | None = None
    industry: str | None = None
    email_domains: list[str] | None = None
    work_id_rule: str | None = None
    keywords: list[str] | None = None
    domains: list[str] | None = None
    ip_ranges: list[str] | None = None
    notes: str | None = None
    website: str | None = None
    logo_url: str | None = None


class CompanyResponse(CompanyBase):
    model_config = {"from_attributes": True}

    id: UUID
    org_id: UUID
    data_source: str | None = None
    last_collected_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    task_count: int = 0
    latest_task_status: str | None = None


class CompanyListResponse(BaseModel):
    data: list[CompanyResponse]
    pagination: Pagination


# ── CompanyRelation ──────────────────────────────────────
class CompanyRelationCreateRequest(BaseModel):
    parent_company_id: UUID
    child_company_id: UUID
    relation_type: str = Field(..., pattern="^(holding|minority_stake|branch|historical)$")
    holding_ratio: float | None = Field(default=None, ge=0, le=100)
    data_source: str | None = None


class CompanyRelationResponse(BaseModel):
    model_config = {"from_attributes": True}

    id: UUID
    parent_company_id: UUID
    child_company_id: UUID
    relation_type: str
    holding_ratio: float | None = None
    data_source: str | None = None
    created_at: datetime


# ── Penetration / graph (A.1-决策3 可配置穿透) ───────────
class PenetrationParams(BaseModel):
    depth: int = Field(default=3, ge=1, le=10)
    holding_ratio_min: float = Field(default=51.0, ge=0, le=100)
    include_minority: bool = False


class GraphNode(BaseModel):
    id: str
    name: str
    type: str = "company"  # company/subsidiary
    holding_ratio: float | None = None
    source: str | None = None  # direct/inherited
    depth: int = 0


class GraphEdge(BaseModel):
    source: str  # parent id
    target: str  # child id
    relation_type: str
    holding_ratio: float | None = None


class CompanyGraphResponse(BaseModel):
    root_id: str
    nodes: list[GraphNode]
    edges: list[GraphEdge]


# ── Risk (A.7) ───────────────────────────────────────────
class CompanyRiskResponse(BaseModel):
    company_id: UUID
    risk_score: float
    asset_count: int
    vuln_count: int
    by_severity: dict[str, int]


class RiskTrendPoint(BaseModel):
    snapshot_at: datetime
    risk_score: float
    asset_count: int
    vuln_count: int


class RiskTrendResponse(BaseModel):
    company_id: UUID
    points: list[RiskTrendPoint]


# ── Company search (C.3-决策4 简称模糊匹配) ──────────────
class CompanySearchHit(BaseModel):
    id: UUID
    name: str
    aliases: list[str] | None = None
    credit_code: str | None = None
    industry: str | None = None


class CompanySearchResponse(BaseModel):
    query: str
    hits: list[CompanySearchHit]


# ── Company enrichment (商业 API 采集) ────────────────────
class EnrichRequest(BaseModel):
    provider: str = Field(default="yuntu", description="采集数据源 (yuntu/...)")
    depth: int = Field(default=3, ge=1, le=10, description="穿透深度")
    holding_min: float = Field(default=50.0, ge=0, le=100, description="持股比例下限 %")
    strategy: str = Field(
        default="auto_fill",
        description="合并策略: auto_fill(只填空字段) / overwrite(覆盖)",
        pattern="^(auto_fill|overwrite)$",
    )
    recursive_depth: int = Field(
        default=0, ge=0, le=3,
        description="递归采集深度：1=采集子公司(三级), 2=采集孙公司(四级)。0=不递归",
    )


class FieldConflictItem(BaseModel):
    field: str
    old_value: object | None = None
    new_value: object | None = None
    old_source: str | None = None
    new_source: str | None = None


class EnrichmentResponse(BaseModel):
    company_id: UUID
    provider: str
    fetched_at: datetime
    updated_fields: list[str] = Field(default_factory=list, description="本次实际写入的字段")
    new_relations: int = 0
    conflicts: list[FieldConflictItem] = Field(default_factory=list, description="需用户对比确认的字段冲突")
    relations: list[CompanyRelationResponse] = Field(default_factory=list)


class EnrichConfirmResolution(BaseModel):
    field: str
    accepted_value: object | None = None  # 旧值或新值


class EnrichConfirmRequest(BaseModel):
    resolutions: list[EnrichConfirmResolution]


class EnrichConfirmResponse(BaseModel):
    company_id: UUID
    applied_fields: list[str] = Field(default_factory=list)


class BatchEnrichRequest(BaseModel):
    company_ids: list[UUID] = Field(..., min_length=1, max_length=50)
    provider: str = "yuntu"
    depth: int = Field(default=3, ge=1, le=10)
    holding_min: float = Field(default=50.0, ge=0, le=100)
    strategy: str = Field(default="auto_fill", pattern="^(auto_fill|overwrite)$")


class BatchEnrichItemResult(BaseModel):
    company_id: UUID
    ok: bool
    error: str | None = None
    new_relations: int = 0
    conflicts: int = 0


class BatchEnrichResponse(BaseModel):
    results: list[BatchEnrichItemResult]
    summary: dict[str, int]


# ── Company detail (聚合视图) ─────────────────────────────
class AssetTypeSummary(BaseModel):
    total: int = 0
    by_type: dict[str, int] = Field(default_factory=dict)


class VulnSummary(BaseModel):
    total: int = 0
    by_severity: dict[str, int] = Field(default_factory=dict)


class SubCompanyView(BaseModel):
    """下属单位精简视图（展开 child_relations 到子公司）。"""

    id: UUID
    name: str
    full_name: str | None = None
    credit_code: str | None = None
    industry: str | None = None
    legal_person: str | None = None
    business_status: str | None = None
    website: str | None = None
    keywords: list[str] | None = None
    domains: list[str] | None = None
    work_id_rule: str | None = None
    holding_ratio: float | None = None
    relation_type: str | None = None
    data_source: str | None = None
    notes: str | None = None


class CompanyDetailResponse(CompanyResponse):
    """企业详情聚合视图：基本信息 + 下属单位 + 资产/漏洞统计。"""

    sub_companies: list[SubCompanyView] = Field(default_factory=list)
    sub_company_count: int = 0
    hierarchy_level: int = 0
    asset_summary: AssetTypeSummary = Field(default_factory=AssetTypeSummary)
    vuln_summary: VulnSummary = Field(default_factory=VulnSummary)
