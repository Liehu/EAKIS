"""Organization model representing a tenant/organization."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import JSON, Boolean, Column, DateTime, Index, Integer, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from .database import Base


class Organization(Base):
    __tablename__ = "organizations"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    slug = Column(String(100), unique=True, nullable=False)
    plan = Column(String(50), nullable=False, server_default="standard")
    max_teams = Column(Integer, nullable=False, server_default="5")
    max_members = Column(Integer, nullable=False, server_default="20")
    settings = Column(JSON, default=dict, nullable=True)
    is_active = Column(Boolean, nullable=False, server_default="true")
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(  # noqa: E501
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC), nullable=False,
    )

    __table_args__ = (
        Index("idx_organizations_slug", "slug"),
    )

    users = relationship("User", back_populates="org")
    teams = relationship("Team", back_populates="org")

    def __repr__(self) -> str:
        return f"<Organization {self.id} {self.name} ({self.slug})>"
