"""Keyword model per docs/extract/10_数据模型设计.md.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, Enum, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from .database import Base

KeywordTypeEnum = Enum(
    "business",
    "tech",
    "entity",
    name="keyword_type",
)

class Keyword(Base):
    __tablename__ = "keywords"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    word = Column(String(200), nullable=False)
    type = Column(KeywordTypeEnum, nullable=False)
    weight = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    source = Column(String, nullable=True)
    source_idx = Column(Integer, nullable=True)
    derived = Column(Boolean, default=False)
    parent_id = Column(PG_UUID(as_uuid=True), ForeignKey("keywords.id"), nullable=True)
    used_in_dsl = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    task = relationship("Task", back_populates="keywords")
    parent = relationship("Keyword", remote_side=[id], backref="children")

    __table_args__ = (
        CheckConstraint("weight BETWEEN 0 AND 1", name="ck_keyword_weight_range"),
        CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_keyword_confidence_range"),
    )

    def __repr__(self) -> str:
        return f"<Keyword {self.id} word={self.word}>"
