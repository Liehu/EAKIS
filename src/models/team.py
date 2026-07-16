"""Team and TeamMember models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from .database import Base


class Team(Base):
    __tablename__ = "teams"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False)
    name = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(  # noqa: E501
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC), nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("org_id", "name", name="uq_team_org_name"),
        Index("idx_teams_org_id", "org_id"),
    )

    org = relationship("Organization", back_populates="teams")
    members = relationship("TeamMember", back_populates="team", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Team {self.id} {self.name}>"


class TeamMember(Base):
    __tablename__ = "team_members"

    team_id = Column(PG_UUID(as_uuid=True), ForeignKey("teams.id", ondelete="CASCADE"), primary_key=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id = Column(PG_UUID(as_uuid=True), ForeignKey("roles.id"), nullable=False)
    joined_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    invited_by = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    __table_args__ = (
        Index("idx_team_members_user_id", "user_id"),
        Index("idx_team_members_role_id", "role_id"),
    )

    team = relationship("Team", back_populates="members")
    user = relationship("User", back_populates="team_members", foreign_keys="[TeamMember.user_id]")
    role = relationship("Role")

    def __repr__(self) -> str:
        return f"<TeamMember user={self.user_id} team={self.team_id}>"
