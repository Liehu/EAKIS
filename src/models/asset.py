"""Asset model based on data model design.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, JSON, DateTime, Enum,
    ForeignKey, UniqueConstraint, CheckConstraint, Index,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY, INET
from sqlalchemy.orm import relationship
from .database import Base, is_postgresql

RiskLevelEnum = Enum(
    "critical", "high", "medium", "low", "info",
    name="risk_level",
)

# A.4-决策2 lifecycle: discovered → confirmed → archived (auto-archive after N misses)
AssetStatusEnum = Enum(
    "discovered", "confirmed", "archived",
    name="asset_status",
)

_InetAddress = INET if is_postgresql() else String(45)
_OpenPortsType = ARRAY(Integer) if is_postgresql() else JSON
_PageKeywordsType = ARRAY(String) if is_postgresql() else JSON


class Asset(Base):
    __tablename__ = "assets"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    # A.1: link asset to its owning company (replaces reliance on task.company_name)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True, index=True)
    domain = Column(String(500), nullable=True)
    ip_address = Column(_InetAddress, nullable=True)
    port = Column(Integer, nullable=True)
    protocol = Column(String(10), nullable=True, server_default="https")
    asset_type = Column(String(50), nullable=True, comment="ip/domain/certificate/miniprogram/app/web")
    confidence_score = Column(Float, nullable=True)
    icp_verified = Column(Boolean, default=False)
    icp_entity = Column(String(500), nullable=True)
    tech_stack = Column(JSON, default=list, nullable=True)
    response_headers = Column(JSON, default=dict, nullable=True)
    page_keywords = Column(_PageKeywordsType, nullable=True)
    waf_type = Column(String(100), nullable=True)
    cert_info = Column(JSON, nullable=True)
    screenshot_path = Column(String, nullable=True)
    open_ports = Column(_OpenPortsType, nullable=True)
    risk_level = Column(RiskLevelEnum, nullable=True, server_default="info")
    confirmed = Column(Boolean, default=False)
    notes = Column(String, nullable=True)
    feature_vector_id = Column(String, nullable=True)

    # ── A.4 生命周期与价值评分 ──
    status = Column(AssetStatusEnum, nullable=False, server_default="discovered", comment="discovered/confirmed/archived")
    value_score = Column(Float, nullable=True, comment="资产价值评分 0-100 (类型×暴露面×业务重要性)")
    last_seen_at = Column(DateTime(timezone=True), nullable=True, comment="最近一次被发现时间")
    miss_count = Column(Integer, nullable=False, default=0, comment="连续未发现次数 (达 N 则自动归档)")

    discovered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("task_id", "domain", "port", name="uq_asset_task_domain_port"),
        UniqueConstraint("task_id", "ip_address", "port", name="uq_asset_task_ip_port"),
        CheckConstraint("confidence_score BETWEEN 0 AND 1", name="ck_asset_confidence_range"),
        CheckConstraint("value_score IS NULL OR value_score BETWEEN 0 AND 100", name="ck_asset_value_range"),
        Index("idx_assets_company_type", "company_id", "asset_type"),
        Index("idx_assets_status", "status"),
    )

    task = relationship("Task", back_populates="assets")
    company = relationship("Company")
    interfaces = relationship("ApiInterface", back_populates="asset", cascade="all, delete-orphan")
    vulnerabilities = relationship("Vulnerability", back_populates="asset", cascade="all, delete-orphan")
    enrichments = relationship("AssetEnrichment", back_populates="asset", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Asset {self.id} domain={self.domain} ip={self.ip_address}>"


class AssetEnrichment(Base):
    """Asset enrichment information from deep scanning."""
    __tablename__ = "asset_enrichments"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    enrichment_type = Column(String(50), nullable=False)
    data = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    asset = relationship("Asset", back_populates="enrichments")

    def __repr__(self) -> str:
        return f"<AssetEnrichment {self.id} type={self.enrichment_type}>"
