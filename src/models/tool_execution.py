"""Tool execution record model (S5 工具管理).

Persists every external tool invocation for traceability and reuse.
Mirrors the payloads.hit_count pattern: execution history enables result
reuse (skip re-running subfinder if a recent run exists for the same domain).
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import (
    Column, DateTime, Float, ForeignKey, Index, Integer, String, Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from .database import Base, is_postgresql
from sqlalchemy import JSON
from sqlalchemy.dialects.postgresql import JSONB

_JsonType = JSONB if is_postgresql() else JSON


class ToolExecution(Base):
    """One run of an external tool (subfinder/dnsx/httpx/...)."""

    __tablename__ = "tool_executions"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_name = Column(String(50), nullable=False, comment="工具名 subfinder/dnsx/...")
    category = Column(String(30), nullable=True, comment="recon/dns/portscan/vulnscan/cert")
    # 关联任务 (可选 — agent 编排调用时填)
    task_id = Column(PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True, index=True)

    # 输入 (归一化后, 已通过白名单校验)
    inputs = Column(_JsonType, nullable=False, default=dict, comment="工具输入 (domain/ip/url 等, 已校验)")
    flags = Column(_JsonType, nullable=True, comment="本次启用的布尔 flag")

    # 执行结果
    status = Column(String(20), nullable=False, comment="success/failed/timeout/unavailable/invalid_input")
    exit_code = Column(Integer, nullable=True)
    stdout = Column(Text, nullable=True)
    stderr = Column(Text, nullable=True)
    parsed = Column(_JsonType, nullable=True, comment="解析后的结构化结果")
    duration_s = Column(Float, nullable=True)
    error = Column(Text, nullable=True)

    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    task = relationship("Task")

    __table_args__ = (
        Index("idx_tool_exec_tool", "tool_name"),
        Index("idx_tool_exec_task", "task_id"),
        Index("idx_tool_exec_status", "status"),
    )

    def __repr__(self) -> str:
        return f"<ToolExecution {self.id} {self.tool_name} {self.status}>"
