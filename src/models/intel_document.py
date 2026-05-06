"""Intel Document model per data model design.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column,
    String,
    Text,
    Float,
    DateTime,
    JSON,
    Boolean,
    UniqueConstraint,
    ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from .database import Base

class IntelDocument(Base):
    __tablename__ = "intel_documents"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    task_id = Column(PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    source_type = Column(String(50), nullable=True)  # news|official|legal|asset_engine
    source_name = Column(String(200), nullable=True)
    source_url = Column(Text, nullable=True)
    content = Column(Text, nullable=False)
    quality_score = Column(Float, nullable=True)
    published_at = Column(DateTime(timezone=True), nullable=True)
    entities = Column(JSON, default=list, nullable=True)
    checksum = Column(String(64), unique=True, nullable=True)
    rag_indexed = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (UniqueConstraint("checksum"),)

    task = relationship("Task", back_populates="intel_documents")

    def __repr__(self) -> str:
        return f"<IntelDocument {self.id} source={self.source_name}>"
