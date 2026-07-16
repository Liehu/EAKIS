"""Template models (S4 模板管理).

Per ROADMAP A.6 decisions (2026-06-17 brainstorm):
- UNIFIED table `templates` + `template_type` distinguishes the 4 kinds:
  task (任务模板=参数预设) / report (报告模板=字段勾选+布局) /
  prompt (LLM 提示词) / attack_path (可视化攻击路径 DAG).
- `content` is a JSON column holding type-specific payload:
    task:        {target_depth, modules:[M1..M6], concurrency, ...params}
    report:      {report_type: asset|company|vuln, fields:[...], layout, format:md|html}
    prompt:      {agent:M2|M6, template:"Jinja2 text with {{vars}}", variables:[...]}
    attack_path: {nodes:[{id,type,label}], edges:[{source,target,action}]}  (DAG JSON)
- Inheritance: `parent_template_id` self-reference; reading a template merges
  parent fields (child overrides subset).
- Visibility scope: org / team / private (A.6-决策5 三级可见域), RBAC-checked.
- Prompt templates: DB is source of truth, config/prompts/ files seed on first run.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from .database import Base, is_postgresql

# JSON column: postgres JSONB, else JSON (sqlite dev)
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

_JsonType = JSONB if is_postgresql() else JSON


class Template(Base):
    """Unified template for task / report / prompt / attack_path (A.6)."""

    __tablename__ = "templates"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id"), nullable=False, index=True)

    name = Column(String(200), nullable=False, comment="模板名称")
    template_type = Column(String(30), nullable=False, comment="task/report/prompt/attack_path")
    description = Column(Text, nullable=True)

    # 类型专属内容 (JSON):
    #   task:        {target_depth, modules, concurrency, ...}
    #   report:      {report_type, fields, layout, format}
    #   prompt:      {agent, template, variables}
    #   attack_path: {nodes, edges}
    content = Column(_JsonType, nullable=False, default=dict, comment="类型专属内容 JSON")

    # 继承 (A.6-决策4): 读取时合并 parent 字段, child override
    parent_template_id = Column(PG_UUID(as_uuid=True), ForeignKey("templates.id"), nullable=True, index=True)

    # 可见域 (A.6-决策5): org(组织级) / team(团队级) / private(个人)
    scope = Column(String(20), nullable=False, server_default="org", comment="org/team/private")
    owner_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, comment="所有者(scope=team/private 时)")
    team_id = Column(PG_UUID(as_uuid=True), ForeignKey("teams.id"), nullable=True, comment="所属团队(scope=team)")

    # 版本 (A.6: 版本化)
    version = Column(Integer, nullable=False, default=1)
    is_active = Column(Integer, nullable=False, default=1, comment="1启用 0禁用")

    # Prompt 种子标记 (从 config/prompts/ 导入的种子标记, 区分用户自建)
    is_seed = Column(Integer, nullable=False, default=0, comment="1=种子(从文件导入) 0=用户自建")

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC), nullable=False,
    )

    parent = relationship("Template", remote_side=[id], backref="children")

    __table_args__ = (
        Index("idx_templates_org_type", "org_id", "template_type"),
        Index("idx_templates_scope", "scope"),
        CheckConstraint(
            "template_type IN ('task', 'report', 'prompt', 'attack_path')",
            name="ck_template_type",
        ),
        CheckConstraint("scope IN ('org', 'team', 'private')", name="ck_template_scope"),
    )

    def __repr__(self) -> str:
        return f"<Template {self.id} {self.template_type}:{self.name}>"


def merge_inherited(child_content: dict | None, parent_content: dict | None) -> dict:
    """合并继承: parent 字段 + child override (A.6-决策4).

    child 的 content 字段 override parent 的同名字段;
    child 未定义的字段继承 parent.
    """
    merged = dict(parent_content or {})
    merged.update(child_content or {})
    return merged
