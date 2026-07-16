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
    # 漏洞计数 (前端 Assets 列表/详情均依赖; 默认全 0 结构避免 undefined)
    vuln_count: dict[str, int] = Field(default_factory=lambda: {"critical": 0, "high": 0, "medium": 0, "low": 0})
    interface_count: int = 0


class AssetListResponse(BaseModel):
    data: list[AssetItem] = Field(default_factory=list)
    pagination: dict = Field(default_factory=dict)


# ── 统一资产视图 (S1 资产多表 + 类型专属字段) ─────────────
class TypedAssetItem(BaseModel):
    """资产统一视图: 公共字段 + 类型专属字段 (type_specific).

    type_specific 内容随 asset_type 变化:
      ip:          {ip_address, is_cdn, asn, region, isp, open_ports}
      domain:      {domain, icp_license, icp_entity, whois_info, registrant, expires_at}
      web:         {url, title, icon, screenshot}
      app:         {name, package_name, platform, version, download_source}
      miniprogram: {name, app_id, platform, subject_entity, category}
      certificate: {common_name, issuer, serial_number, expires_at, is_expired}
    """
    id: str
    asset_type: str
    domain: str | None = None
    ip_address: str | None = None
    port: int | None = None
    risk_level: str = "info"
    confidence: float = 0.0
    confirmed: bool = False
    company_id: str | None = None
    company_name: str | None = None
    tech_stack: list[str] = Field(default_factory=list)
    icp_entity: str | None = None
    waf_type: str | None = None
    status: str = "discovered"
    source: str | None = None  # 来源: manual/icp/dns/smart_link
    notes: str | None = None
    discovered_at: str | None = None
    vuln_count: dict[str, int] = Field(default_factory=lambda: {"critical": 0, "high": 0, "medium": 0, "low": 0})
    type_specific: dict = Field(default_factory=dict, description="类型专属字段")


class TypedAssetListResponse(BaseModel):
    data: list[TypedAssetItem] = Field(default_factory=list)
    pagination: dict = Field(default_factory=dict)


class AssetDetailResponse(AssetItem):
    """资产详情 (与 AssetItem 一致, 保留以兼容现有引用)."""


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
