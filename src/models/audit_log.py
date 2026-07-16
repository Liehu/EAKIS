"""AuditLog model for operation auditing."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import JSON, BigInteger, Column, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from .database import Base, is_postgresql

_InetAddress = type("INET", (), {})()  # placeholder
if is_postgresql():
    from sqlalchemy.dialects.postgresql import INET as _InetAddress  # noqa: N811
else:
    _InetAddress = String(45)  # type: ignore[assignment]


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    user_id = Column(PG_UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    username = Column(String(300), nullable=True)
    org_id = Column(PG_UUID(as_uuid=True), nullable=True)
    team_id = Column(PG_UUID(as_uuid=True), nullable=True)
    action = Column(String(100), nullable=False)
    resource_type = Column(String(50), nullable=False)
    resource_id = Column(String(100), nullable=True)
    ip_address = Column(_InetAddress, nullable=True)
    user_agent = Column(Text, nullable=True)
    request_method = Column(String(10), nullable=True)
    request_path = Column(String(500), nullable=True)
    status_code = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    detail = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False)

    __table_args__ = (
        Index("idx_audit_logs_created_at", "created_at"),
        Index("idx_audit_logs_user_id", "user_id"),
        Index("idx_audit_logs_org_id", "org_id"),
        Index("idx_audit_logs_action", "action"),
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.id} action={self.action}>"
