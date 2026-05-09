"""Pydantic schemas for asset API endpoints (section 9.4)."""

from __future__ import annotations

from pydantic import BaseModel, Field


# --- Request schemas ---


class DiscoveryStartRequest(BaseModel):
    dsl_queries: list[dict[str, str]] = Field(
        ...,
        min_length=1,
        description="List of {platform, query} DSL queries to search",
    )
    company_name: str | None = None
    target_domains: list[str] | None = None
    target_icp_entity: str | None = None
    target_ip_ranges: list[str] | None = None


class AssetUpdateRequest(BaseModel):
    confirmed: bool | None = None
    risk_level: str | None = Field(default=None, pattern="^(critical|high|medium|low|info)$")
    notes: str | None = None


# --- Response schemas ---


class CertInfoItem(BaseModel):
    subject: str = ""
    issuer: str = ""
    expires_at: str | None = None


class AssetItem(BaseModel):
    id: str
    domain: str | None = None
    ip_address: str | None = None
    port: int | None = None
    protocol: str = "https"
    asset_type: str = "web"
    confidence: float = 0.0
    risk_level: str = "info"
    icp_verified: bool = False
    icp_entity: str | None = None
    waf_detected: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    open_ports: list[int] = Field(default_factory=list)
    cert_info: CertInfoItem = Field(default_factory=CertInfoItem)
    screenshot_path: str | None = None
    confirmed: bool = False
    notes: str | None = None
    discovered_at: str | None = None


class AssetListResponse(BaseModel):
    data: list[AssetItem] = Field(default_factory=list)
    pagination: dict = Field(default_factory=dict)


class AssetDetailResponse(AssetItem):
    vuln_count: dict[str, int] = Field(default_factory=dict)
    interface_count: int = 0


class DiscoveryStartResponse(BaseModel):
    task_id: str
    status: str
    total_searched: int = 0
    total_candidates: int = 0
    total_confirmed: int = 0
    total_enriched: int = 0
    by_asset_type: dict[str, int] = Field(default_factory=dict)
    avg_confidence: float = 0.0
    errors: list[str] = Field(default_factory=list)


class DiscoveryStatusResponse(BaseModel):
    task_id: str
    status: str
    total_assets: int = 0
    total_confirmed: int = 0
    by_asset_type: dict[str, int] = Field(default_factory=dict)
    avg_confidence: float = 0.0
