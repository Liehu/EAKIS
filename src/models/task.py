"""Task model representing a detection task.
Based on the SQL definition in docs/extract/10_数据模型设计.md.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Float, Integer, JSON, DateTime, Enum, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY
from sqlalchemy.orm import relationship
from .database import Base, is_postgresql

TaskStatusEnum = Enum(
    "pending", "running", "paused", "completed", "failed", "cancelled",
    name="task_status",
)

_CompanyAliasesType = ARRAY(Text) if is_postgresql() else JSON


class Task(Base):
    __tablename__ = "tasks"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_name = Column(String(200), nullable=False)
    company_aliases = Column(_CompanyAliasesType, nullable=True)
    industry = Column(String(50), nullable=True)
    status = Column(TaskStatusEnum, nullable=False, server_default="pending")
    current_stage = Column(String(50), nullable=True)
    progress = Column(Float, default=0.0, nullable=False)
    authorized_scope = Column(JSON, nullable=False)
    config = Column(JSON, default=dict, nullable=True)
    error_message = Column(Text, nullable=True)
    retry_count = Column(Integer, default=0)
    created_by = Column(String(100), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    metadata_ = Column("metadata", JSON, default=dict, nullable=True)

    keywords = relationship("Keyword", back_populates="task", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="task", cascade="all, delete-orphan")
    intel_documents = relationship("IntelDocument", back_populates="task", cascade="all, delete-orphan")
    agent_logs = relationship("AgentLog", back_populates="task", cascade="all, delete-orphan")
    reports = relationship("Report", back_populates="task", cascade="all, delete-orphan")
    vulnerabilities = relationship("Vulnerability", back_populates="task", cascade="all, delete-orphan")

    __table_args__ = (
        CheckConstraint("progress BETWEEN 0 AND 1", name="ck_progress_range"),
    )

    def __repr__(self) -> str:
        return f"<Task {self.id} {self.company_name} status={self.status}>"
