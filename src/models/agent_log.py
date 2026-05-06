"""AgentLog model per docs/extract/10_数据模型设计.md.
"""

from datetime import datetime, timezone
from sqlalchemy import (
    Column, BigInteger, String, Text, JSON, DateTime, ForeignKey,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import relationship
from .database import Base


class AgentLog(Base):
    __tablename__ = "agent_logs"

    id = Column(BigInteger, primary_key=True, autoincrement=True)
    task_id = Column(PG_UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    agent_name = Column(String(100), nullable=False)
    level = Column(String(10), nullable=False)
    message = Column(Text, nullable=False)
    context = Column(JSON, default=dict, nullable=True)
    trace_id = Column(String(64), nullable=True)
    span_id = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    task = relationship("Task", back_populates="agent_logs")

    def __repr__(self) -> str:
        return f"<AgentLog {self.id} agent={self.agent_name} level={self.level}>"
