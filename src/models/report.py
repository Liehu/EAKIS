"""Report model per docs/extract/10_数据模型设计.md.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Integer, JSON, DateTime, Enum,
    ForeignKey, Text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from .database import Base

ReportStatusEnum = Enum(
    "generating", "completed", "failed",
    name="report_status",
)


class Report(Base):
    __tablename__ = "reports"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    status = Column(ReportStatusEnum, nullable=False, server_default="generating")
    template = Column(String(50), nullable=True, server_default="standard")
    language = Column(String(10), nullable=True, server_default="zh-CN")
    markdown_path = Column(Text, nullable=True)
    pdf_path = Column(Text, nullable=True)
    page_count = Column(Integer, nullable=True)
    word_count = Column(Integer, nullable=True)
    quality_score = Column(JSON, default=dict, nullable=True)
    generation_duration_s = Column(Integer, nullable=True)
    error_message = Column(Text, nullable=True)
    generated_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    task = relationship("Task", back_populates="reports")

    def __repr__(self) -> str:
        return f"<Report {self.id} status={self.status}>"
