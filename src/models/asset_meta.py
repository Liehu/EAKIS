"""Asset metadata tables: lifecycle history, tags, and risk snapshots.

Implements A.4 (资产管理) and A.7 (风险评估关联) from docs/ROADMAP.md:
- AssetHistory: field-level change log for rescans (新增/消失/变更 three columns).
- AssetTag: user-defined + system auto tags, shared with knowledge base tags (A.2).
- RiskHistory: per-task risk snapshot for trend charts.

Note: Asset/Domain/IP/Certificate/etc. models live in their own modules (asset.py,
asset_types.py). These meta tables reference the base assets table for lifecycle,
and companies for risk aggregation.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from .database import Base


class AssetHistory(Base):
    """Field-level change log for an asset across rescans (A.4-决策4).

    One row per (asset, field, change). Used to render 新增/消失/变更 diff views.
    """

    __tablename__ = "asset_history"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    field = Column(String(50), nullable=False, comment="变更字段 (e.g. open_ports/risk_level/tech_stack)")
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    change_type = Column(String(20), nullable=False, comment="added/removed/changed")
    changed_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = (
        Index("idx_asset_history_asset", "asset_id"),
        Index("idx_asset_history_task", "task_id"),
    )

    def __repr__(self) -> str:
        return f"<AssetHistory {self.asset_id} {self.field} {self.change_type}>"


class AssetTag(Base):
    """Tag on an asset — user-defined or system-auto (by tech stack / industry).

    Shared tag taxonomy with the knowledge base (A.2-决策4). scope:
    system(自动) / user(人工).
    """

    __tablename__ = "asset_tags"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    tag = Column(String(100), nullable=False)
    scope = Column(String(20), nullable=False, server_default="user", comment="system/user")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = (
        UniqueConstraint("asset_id", "tag", "scope", name="uq_asset_tag"),
        Index("idx_asset_tags_asset", "asset_id"),
        Index("idx_asset_tags_tag", "tag"),
    )

    def __repr__(self) -> str:
        return f"<AssetTag {self.asset_id} #{self.tag}>"


class RiskHistory(Base):
    """Per-task risk snapshot for a company (A.7-决策2 趋势).

    Written at task completion. company_risk = Σ asset_risk; asset_risk =
    Σ(vuln.cvss × severity_weight). See ROADMAP A.7 risk formula.
    """

    __tablename__ = "risk_history"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    risk_score = Column(Float, nullable=False, default=0.0, comment="企业风险分 (capped 0-100)")
    asset_count = Column(Integer, nullable=False, default=0)
    vuln_count = Column(Integer, nullable=False, default=0)
    by_severity = Column(JSON, nullable=False, default=dict, comment="{critical,high,medium,low}")
    snapshot_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = (
        Index("idx_risk_history_company", "company_id"),
        Index("idx_risk_history_snapshot", "snapshot_at"),
    )

    def __repr__(self) -> str:
        return f"<RiskHistory {self.company_id} score={self.risk_score} at={self.snapshot_at}>"
