"""Asset model based on data model design.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, JSON, DateTime, Enum,
    ForeignKey, UniqueConstraint, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY, INET
from sqlalchemy.orm import relationship
from .database import Base, is_postgresql

RiskLevelEnum = Enum(
    "critical", "high", "medium", "low", "info",
    name="risk_level",
)

_InetAddress = INET if is_postgresql() else String(45)
_OpenPortsType = ARRAY(Integer) if is_postgresql() else JSON
_PageKeywordsType = ARRAY(String) if is_postgresql() else JSON


class Asset(Base):
    __tablename__ = "assets"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    domain = Column(String(500), nullable=True)
    ip_address = Column(_InetAddress, nullable=True)
    port = Column(Integer, nullable=True)
    protocol = Column(String(10), nullable=True, server_default="https")
    asset_type = Column(String(50), nullable=True)
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
    discovered_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("task_id", "domain", "port", name="uq_asset_task_domain_port"),
        UniqueConstraint("task_id", "ip_address", "port", name="uq_asset_task_ip_port"),
        CheckConstraint("confidence_score BETWEEN 0 AND 1", name="ck_asset_confidence_range"),
    )

    task = relationship("Task", back_populates="assets")
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
