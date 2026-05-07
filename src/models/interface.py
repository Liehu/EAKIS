"""API Interface model as defined in the data model design.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import (
    Column, String, Text, Integer, Boolean, JSON, DateTime,
    ForeignKey, CheckConstraint,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, ARRAY
from sqlalchemy.orm import relationship
from .database import Base, is_postgresql

_SensitiveParamsType = ARRAY(String) if is_postgresql() else JSON


class ApiInterface(Base):
    __tablename__ = "interfaces"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    asset_id = Column(PG_UUID(as_uuid=True), ForeignKey("assets.id", ondelete="CASCADE"), nullable=False)
    task_id = Column(PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    path = Column(Text, nullable=False)
    path_pattern = Column(Text, nullable=True)
    method = Column(String(10), nullable=False)
    api_type = Column(String(50), nullable=True)
    parameters = Column(JSON, default=list, nullable=True)
    request_headers = Column(JSON, default=dict, nullable=True)
    response_schema = Column(JSON, default=dict, nullable=True)
    auth_required = Column(Boolean, default=True)
    privilege_sensitive = Column(Boolean, default=False)
    sensitive_params = Column(_SensitiveParamsType, nullable=True)
    trigger_scenario = Column(Text, nullable=True)
    crawl_method = Column(String(20), nullable=True)
    test_priority = Column(Integer, default=5, nullable=False)
    skip_test = Column(Boolean, default=False)
    notes = Column(Text, nullable=True)
    feature_embedding_id = Column(String, nullable=True)
    version = Column(Integer, default=1)
    checksum = Column(String(64), nullable=True)
    crawled_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        CheckConstraint("test_priority BETWEEN 1 AND 10", name="ck_test_priority_range"),
    )

    asset = relationship("Asset", back_populates="interfaces")
    vulnerabilities = relationship("Vulnerability", back_populates="interface", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<ApiInterface {self.id} {self.method} {self.path}>"
