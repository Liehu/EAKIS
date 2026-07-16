"""Knowledge base models (S3 知识库管理).

Per ROADMAP A.2 + user decisions (2026-06-17 brainstorm):
- 6 independent tables, NOT a unified table.
- 漏洞知识库 (vuln_knowledge, renamed from nuclei) carries full vuln fields and
  a 1:1 fingerprint_id FK (fingerprint ↔ vuln is 1:N).
- payloads MERGES 密码字典/路径字典/关键词库 into one table, distinguished by
  `category` (pass/path/user/header/payload/keywords) and `group_name`
  (ua/header/常见用户名/常见密码/行业关键词). Each item is one row with a TEXT
  `content` field that may contain multi-line strings (newlines). `weight` is a
  user-preset/adjustable priority; `hit_count` auto-increments on each match.
  NO status field (payloads are immediately usable).
- Audit workflow (draft→pending_review→published→deprecated) applies to
  vuln_knowledge / fingerprint / handbook (A.2-决策3), NOT to payloads/datasources.
- knowledge_tags is an independent table shared across knowledge types
  (A.2-决策4 tag filtering, shared taxonomy with asset tags).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
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

from .database import Base

# A.2-决策3 audit state machine
KnowledgeStatusEnum = Enum(
    "draft", "pending_review", "published", "deprecated",
    name="knowledge_status",
)

# payloads.category enum-like (kept as String for flexibility)
PAYLOAD_CATEGORIES = ("pass", "path", "user", "header", "payload", "keywords")


# ── 漏洞知识库 (原 nuclei) ────────────────────────────────
class VulnKnowledge(Base):
    """漏洞知识库 — 替换原 nuclei-pocs。

    一个漏洞关联一个指纹 (fingerprint_id, 1:1);
    一个指纹可被多个漏洞引用 (fingerprint 侧 1:N).
    """

    __tablename__ = "vuln_knowledge"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(300), nullable=False, comment="漏洞名称")
    severity = Column(String(20), nullable=False, comment="critical/high/medium/low/info")
    vuln_id = Column(String(100), nullable=True, comment="漏洞编号 CVE/CNVD/CNNVD 等")
    vuln_type = Column(String(100), nullable=True, comment="漏洞类型 SQLi/XSS/SSRF 等")

    # 厂商/产品/版本/影响范围
    vendor = Column(String(200), nullable=True, comment="厂商名称")
    product = Column(String(200), nullable=True, comment="产品名称")
    version_range = Column(String(200), nullable=True, comment="影响版本型号")
    affected_scope = Column(Text, nullable=True, comment="影响范围描述")

    # 指纹关联 (1:1 — 漏洞关联到一个指纹)
    fingerprint_id = Column(PG_UUID(as_uuid=True), ForeignKey("fingerprints.id"), nullable=True, index=True)

    # POC / Payload / 修复
    poc = Column(Text, nullable=True, comment="POC/Payload (YAML/文本, 支持多行)")
    remediation = Column(Text, nullable=True, comment="修复方案")

    # 来源 / 版本
    data_source = Column(String(50), nullable=True, comment="来源 (upstream/manual)")
    upstream_ref = Column(String(200), nullable=True, comment="上游引用 (e.g. nuclei template id / commit)")

    # 审核流 (A.2-决策3)
    status = Column(KnowledgeStatusEnum, nullable=False, server_default="draft")
    contributed_by = Column(String(100), nullable=True, comment="贡献者")
    reviewed_by = Column(String(100), nullable=True, comment="审核人")
    review_comment = Column(Text, nullable=True, comment="审核意见")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC), nullable=False,
    )

    fingerprint = relationship("Fingerprint", back_populates="vulns")
    tags = relationship("KnowledgeTag", back_populates="vuln", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_vuln_knowledge_severity", "severity"),
        Index("idx_vuln_knowledge_vuln_id", "vuln_id"),
        Index("idx_vuln_knowledge_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<VulnKnowledge {self.id} {self.name}>"


# ── 指纹库 ────────────────────────────────────────────────
class Fingerprint(Base):
    """指纹库 — Web 应用/框架/服务指纹识别规则。

    被漏洞知识库 1:N 引用 (一个指纹组件可有多个漏洞).
    被 M3 feature_extractor 消费识别资产技术栈.
    """

    __tablename__ = "fingerprints"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False, comment="指纹名称/组件名")
    category = Column(String(50), nullable=True, comment="分类 web/framework/service/os")
    component = Column(String(200), nullable=True, comment="组件 (e.g. Nginx/Apache/Spring)")
    version = Column(String(100), nullable=True, comment="版本")
    # 匹配规则: HTTP header / body / favicon hash / cookie 等
    match_type = Column(String(50), nullable=True, comment="匹配方式 header/body/favicon/cookie")
    match_rule = Column(Text, nullable=False, comment="匹配规则 (正则/字符串/hash)")
    description = Column(Text, nullable=True)

    data_source = Column(String(50), nullable=True)
    status = Column(KnowledgeStatusEnum, nullable=False, server_default="draft")
    contributed_by = Column(String(100), nullable=True)
    reviewed_by = Column(String(100), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC), nullable=False,
    )

    vulns = relationship("VulnKnowledge", back_populates="fingerprint")
    tags = relationship("KnowledgeTag", back_populates="fingerprint", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_fingerprints_component", "component"),
        Index("idx_fingerprints_category", "category"),
    )

    def __repr__(self) -> str:
        return f"<Fingerprint {self.id} {self.name}>"


# ── Payloads (合并 密码/路径/关键词库) ────────────────────
class Payload(Base):
    """Payloads — 合并密码字典/路径字典/关键词库.

    category 区分类型: pass(密码) / path(路径) / user(用户名) / header(请求头) /
                       payload(攻击载荷) / keywords(关键词).
    group_name 区分组: ua/header/常见用户名/常见密码/行业关键词 等.
    content 支持换行多行字符串 (一个 User-Agent 项可含多行).
    weight 用户预设可调权重 (查询排序用); hit_count 命中自动 +1 (统计用).
    无审核流, 直接可用.
    """

    __tablename__ = "payloads"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=True, comment="项名称 (可选)")
    content = Column(Text, nullable=False, comment="字典内容 (支持换行多行字符串)")
    category = Column(String(50), nullable=False, comment="pass/path/user/header/payload/keywords")
    group_name = Column(String(100), nullable=True, comment="分组 ua/header/常见用户名/常见密码/行业关键词")
    weight = Column(Float, nullable=False, default=1.0, comment="用户预设权重 (可调, 排序用)")
    hit_count = Column(Integer, nullable=False, default=0, comment="命中次数 (自动 +1)")
    description = Column(Text, nullable=True)
    data_source = Column(String(50), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC), nullable=False,
    )

    tags = relationship("KnowledgeTag", back_populates="payload", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_payloads_category", "category"),
        Index("idx_payloads_group", "group_name"),
        Index("idx_payloads_weight", "weight"),
    )

    def __repr__(self) -> str:
        return f"<Payload {self.id} cat={self.category} group={self.group_name}>"


# ── 数据源定义 ────────────────────────────────────────────
class KnowledgeDatasource(Base):
    """数据源定义 — Fofa/Shodan/Hunter 等平台配置 (供 M1 情报采集消费)."""

    __tablename__ = "knowledge_datasources"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, comment="数据源名称")
    platform = Column(String(50), nullable=False, comment="平台 fofa/shodan/hunter/quake 等")
    api_base_url = Column(String(500), nullable=True)
    config = Column(Text, nullable=True, comment="配置 JSON (字段映射/认证/限流)")
    description = Column(Text, nullable=True)
    is_active = Column(Integer, nullable=False, default=1, comment="1启用 0禁用")

    # 数据源无审核流，直接可用
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC), nullable=False,
    )

    tags = relationship("KnowledgeTag", back_populates="datasource", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint("platform", "name", name="uq_datasource_platform_name"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeDatasource {self.id} {self.platform}:{self.name}>"


# ── 攻防经验手册 ──────────────────────────────────────────
class KnowledgeHandbook(Base):
    """攻防经验手册 — 攻防经验与案例知识库."""

    __tablename__ = "knowledge_handbooks"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title = Column(String(300), nullable=False, comment="标题")
    category = Column(String(100), nullable=True, comment="分类 攻击案例/防御方案/应急响应")
    content = Column(Text, nullable=False, comment="正文 (Markdown)")
    summary = Column(Text, nullable=True, comment="摘要")

    data_source = Column(String(50), nullable=True)
    status = Column(KnowledgeStatusEnum, nullable=False, server_default="draft")
    contributed_by = Column(String(100), nullable=True)
    reviewed_by = Column(String(100), nullable=True)
    review_comment = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC), nullable=False,
    )

    tags = relationship("KnowledgeTag", back_populates="handbook", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_knowledge_handbooks_category", "category"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeHandbook {self.id} {self.title}>"


# ── 标签 (独立表, 关联各类知识) ────────────────────────────
class KnowledgeTag(Base):
    """知识标签 — 独立表关联各类知识条目 (A.2-决策4).

    一条标签记录关联到一种知识 (vuln/fingerprint/payload/datasource/handbook),
    其中仅一个 *_id 非空。tag 值如技术栈(Java/PHP)/场景(认证/上传)/行业.
    scope: system(自动) / user(人工).
    """

    __tablename__ = "knowledge_tags"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tag = Column(String(100), nullable=False)
    scope = Column(String(20), nullable=False, server_default="user", comment="system/user")

    # 多态关联 — 仅一个非空
    vuln_id = Column(PG_UUID(as_uuid=True), ForeignKey("vuln_knowledge.id", ondelete="CASCADE"), nullable=True)
    fingerprint_id = Column(PG_UUID(as_uuid=True), ForeignKey("fingerprints.id", ondelete="CASCADE"), nullable=True)
    payload_id = Column(PG_UUID(as_uuid=True), ForeignKey("payloads.id", ondelete="CASCADE"), nullable=True)
    datasource_id = Column(PG_UUID(as_uuid=True), ForeignKey("knowledge_datasources.id", ondelete="CASCADE"), nullable=True)
    handbook_id = Column(PG_UUID(as_uuid=True), ForeignKey("knowledge_handbooks.id", ondelete="CASCADE"), nullable=True)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    vuln = relationship("VulnKnowledge", back_populates="tags")
    fingerprint = relationship("Fingerprint", back_populates="tags")
    payload = relationship("Payload", back_populates="tags")
    datasource = relationship("KnowledgeDatasource", back_populates="tags")
    handbook = relationship("KnowledgeHandbook", back_populates="tags")

    __table_args__ = (
        Index("idx_knowledge_tags_tag", "tag"),
        Index("idx_knowledge_tags_scope", "scope"),
    )

    def __repr__(self) -> str:
        return f"<KnowledgeTag #{self.tag} scope={self.scope}>"
