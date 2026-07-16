"""Company and company relationship models.

Implements A.1 (企业关系穿透) from docs/ROADMAP.md:
- Company: target entity being investigated (distinct from Organization which is
  the RBAC tenant). Replaces the legacy Task.company_name string with a real entity.
- CompanyRelation: arbitrary relationships between companies (控股/参股/分支机构/
  历史关联) supporting multi-level penetration (default 3 levels + holding ≥ 51%,
  configurable per task).

工商字段 (名称/信用代码/注册资本/成立时间/法人/存续状态) are collected read-only from
商业 API/OSINT; 业务字段 (邮箱域名/员工工号规则/标签/备注/关键词) are user-editable.
See ROADMAP C.2-决策1.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from .database import Base, is_postgresql

# ARRAY falls back to JSON on SQLite (dev).
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import ARRAY

_ArrayType = ARRAY(String) if is_postgresql() else JSON


class Company(Base):
    """A target company being investigated. One company may own many sub-units."""

    __tablename__ = "companies"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # org_id: which tenant (Organization) owns this company record (RBAC scoping).
    org_id = Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False)

    # ── 工商字段 (collected, read-only) ──
    name = Column(String(300), nullable=False, comment="企业全称")
    aliases = Column(_ArrayType, nullable=True, comment="简称/曾用名")
    credit_code = Column(String(64), nullable=True, comment="统一社会信用代码")
    industry = Column(String(100), nullable=True, comment="行业")
    registered_capital = Column(String(50), nullable=True, comment="注册资本")
    established_at = Column(DateTime(timezone=True), nullable=True, comment="成立时间")
    legal_person = Column(String(100), nullable=True, comment="法定代表人")
    business_status = Column(String(50), nullable=True, comment="存续状态")
    website = Column(String(500), nullable=True, comment="官网")
    logo_url = Column(String(500), nullable=True, comment="图标")

    # ── 业务字段 (user-editable) ──
    email_domains = Column(_ArrayType, nullable=True, comment="邮箱域名 (生成账号/邮箱字典)")
    work_id_rule = Column(String(100), nullable=True, comment="员工工号规则 (生成账号字典)")
    keywords = Column(_ArrayType, nullable=True, comment="业务关键词")
    domains = Column(_ArrayType, nullable=True, comment="ICP 备案域名")
    ip_ranges = Column(_ArrayType, nullable=True, comment="IP 段")
    notes = Column(Text, nullable=True, comment="备注")

    # ── 采集元信息 ──
    data_source = Column(String(50), nullable=True, comment="数据来源 (商业API/ICP/OSINT)")
    last_collected_at = Column(DateTime(timezone=True), nullable=True, comment="最近采集时间")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC), nullable=False,
    )

    # ── 关系 ──
    # parent_relations: relations where this company is the child
    # child_relations: relations where this company is the parent
    parent_relations = relationship(
        "CompanyRelation", foreign_keys="CompanyRelation.child_company_id",
        back_populates="child", cascade="all, delete-orphan",
    )
    child_relations = relationship(
        "CompanyRelation", foreign_keys="CompanyRelation.parent_company_id",
        back_populates="parent", cascade="all, delete-orphan",
    )
    tasks = relationship("Task", back_populates="company")

    __table_args__ = (
        Index("idx_companies_org", "org_id"),
        Index("idx_companies_credit_code", "credit_code"),
        Index("idx_companies_name", "name"),
    )

    def __repr__(self) -> str:
        return f"<Company {self.id} {self.name}>"


class CompanyRelation(Base):
    """Relationship between two companies (parent → child).

    relation_type: holding(控股) / minority_stake(参股) / branch(分支机构) /
                   historical(历史关联)
    holding_ratio: 持股比例 0-100 (NULL for branch/historical)
    """

    __tablename__ = "company_relations"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_company_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
    )
    child_company_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False,
    )
    relation_type = Column(String(30), nullable=False, comment="关系类型")
    holding_ratio = Column(Float, nullable=True, comment="持股比例 0-100")
    data_source = Column(String(50), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    parent = relationship("Company", foreign_keys=[parent_company_id], back_populates="child_relations")
    child = relationship("Company", foreign_keys=[child_company_id], back_populates="parent_relations")

    __table_args__ = (
        UniqueConstraint("parent_company_id", "child_company_id", "relation_type", name="uq_company_relation"),
        Index("idx_company_relations_parent", "parent_company_id"),
        Index("idx_company_relations_child", "child_company_id"),
        CheckConstraint("holding_ratio IS NULL OR holding_ratio BETWEEN 0 AND 100", name="ck_holding_ratio_range"),
        CheckConstraint("parent_company_id != child_company_id", name="ck_no_self_relation"),
    )

    def __repr__(self) -> str:
        return f"<CompanyRelation {self.parent_company_id}->{self.child_company_id} {self.relation_type}>"
