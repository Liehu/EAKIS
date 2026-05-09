from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from enum import Enum


class AssetType(str, Enum):
    WEB = "web"
    API = "api"
    MOBILE = "mobile"
    INFRA = "infra"


class RiskLevel(str, Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class DiscoveryStatus(str, Enum):
    PENDING = "pending"
    SEARCHING = "searching"
    ASSESSING = "assessing"
    ENRICHING = "enriching"
    COMPLETED = "completed"
    PARTIAL_FAILURE = "partial_failure"
    FAILED = "failed"


@dataclass
class RawAsset:
    domain: str | None = None
    ip_address: str | None = None
    port: int | None = None
    protocol: str = "https"
    source_platform: str = ""
    source_query: str = ""
    title: str = ""
    headers: dict = field(default_factory=dict)
    body_snippet: str = ""
    icp_entity: str | None = None
    cert_info: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    @property
    def dedup_key(self) -> str:
        parts = [self.ip_address or "", str(self.port or ""), self.domain or ""]
        return "|".join(parts)


@dataclass
class FeatureVector:
    icp_entity: float = 0.0
    domain_pattern: float = 0.0
    ip_attribution: float = 0.0
    header_features: float = 0.0
    page_keywords: float = 0.0

    WEIGHTS = {
        "icp_entity": 0.35,
        "domain_pattern": 0.25,
        "ip_attribution": 0.20,
        "header_features": 0.12,
        "page_keywords": 0.08,
    }

    def to_list(self) -> list[float]:
        return [
            self.icp_entity,
            self.domain_pattern,
            self.ip_attribution,
            self.header_features,
            self.page_keywords,
        ]

    def weighted_score(self) -> float:
        total = 0.0
        for dim, weight in self.WEIGHTS.items():
            total += getattr(self, dim) * weight
        return total


@dataclass
class AssessedAsset:
    raw: RawAsset
    confidence: float = 0.0
    feature_vector: FeatureVector = field(default_factory=FeatureVector)
    matched_rules: list[str] = field(default_factory=list)
    asset_type: AssetType = AssetType.WEB
    icp_verified: bool = False


@dataclass
class EnrichedAsset:
    asset_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    raw: RawAsset = field(default_factory=RawAsset)
    confidence: float = 0.0
    asset_type: AssetType = AssetType.WEB
    icp_verified: bool = False
    tech_stack: list[str] = field(default_factory=list)
    open_ports: list[int] = field(default_factory=list)
    waf_type: str | None = None
    cert_info: dict = field(default_factory=dict)
    screenshot_path: str | None = None
    risk_level: RiskLevel = RiskLevel.INFO
    feature_vector_id: str | None = None
    notes: str | None = None
    confirmed: bool = False

    @property
    def domain(self) -> str | None:
        return self.raw.domain

    @property
    def ip_address(self) -> str | None:
        return self.raw.ip_address

    @property
    def port(self) -> int | None:
        return self.raw.port


@dataclass
class DiscoveryResult:
    task_id: str
    status: DiscoveryStatus
    total_searched: int = 0
    total_candidates: int = 0
    total_confirmed: int = 0
    total_enriched: int = 0
    by_asset_type: dict[str, int] = field(default_factory=dict)
    avg_confidence: float = 0.0
    errors: list[str] = field(default_factory=list)
