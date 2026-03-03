"""
database/models/tasks.py
SQLAlchemy model for the tasks table.
"""

from sqlalchemy import Column, String, Integer, JSON, TIMESTAMP, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from database.models.users import Base


class Task(Base):
    __tablename__ = "tasks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workflow_type = Column(String, nullable=False)
    status = Column(String, nullable=False, default="pending")
    input_data = Column(JSON, default=dict)
    output_data = Column(JSON, default=dict)
    error_message = Column(String, nullable=True)
    agent_trace_id = Column(String, nullable=True)
    tokens_used = Column(Integer, default=0)
    duration_ms = Column(Integer, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    completed_at = Column(TIMESTAMP(timezone=True), nullable=True)

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "workflow_type": self.workflow_type,
            "status": self.status,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error_message": self.error_message,
            "agent_trace_id": self.agent_trace_id,
            "tokens_used": self.tokens_used,
            "duration_ms": self.duration_ms,
            "created_at": str(self.created_at),
            "completed_at": str(self.completed_at) if self.completed_at else None,
        }
