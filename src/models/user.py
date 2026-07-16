"""User and UserRefreshToken models."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship

from .database import Base, is_postgresql

_InetAddress = type("INET", (), {})()  # placeholder
if is_postgresql():
    from sqlalchemy.dialects.postgresql import INET as _InetAddress  # noqa: N811
else:
    _InetAddress = String(45)  # type: ignore[assignment]


class User(Base):
    __tablename__ = "users"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    org_id = Column(PG_UUID(as_uuid=True), ForeignKey("organizations.id", ondelete="RESTRICT"), nullable=False)
    email = Column(String(300), nullable=False)
    hashed_password = Column(Text, nullable=False)
    display_name = Column(String(100), nullable=False)
    phone = Column(String(50), nullable=True)
    avatar_url = Column(String(500), nullable=True)
    is_active = Column(Boolean, nullable=False, default=True, server_default="1")
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    updated_at = Column(  # noqa: E501
        DateTime(timezone=True), default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC), nullable=False,
    )

    __table_args__ = (
        UniqueConstraint("org_id", "email", name="uq_user_org_email"),
        Index("idx_users_org_id", "org_id"),
        Index("idx_users_email", "email"),
    )

    org = relationship("Organization", back_populates="users")
    team_members = relationship(  # noqa: E501
        "TeamMember", back_populates="user", cascade="all, delete-orphan",
        foreign_keys="[TeamMember.user_id]",
    )
    refresh_tokens = relationship("UserRefreshToken", back_populates="user", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<User {self.id} {self.email}>"


class UserRefreshToken(Base):
    __tablename__ = "user_refresh_tokens"

    id = Column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    token_hash = Column(String(128), nullable=False)
    device_info = Column(Text, nullable=True)
    ip_address = Column(_InetAddress, nullable=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)
    revoked_at = Column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("idx_refresh_tokens_user", "user_id"),
    )

    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self) -> str:
        return f"<UserRefreshToken {self.id} user={self.user_id}>"
