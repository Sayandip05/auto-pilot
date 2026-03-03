"""
database/models/audit_logs.py
SQLAlchemy model for audit logs.
"""

from sqlalchemy import Column, String, JSON, TIMESTAMP, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from database.models.users import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    task_id = Column(UUID(as_uuid=True), ForeignKey("tasks.id", ondelete="SET NULL"), nullable=True)
    service = Column(String, nullable=False)
    agent_name = Column(String, nullable=True)
    action = Column(String, nullable=False)
    details = Column(JSON, default=dict)
    ip_address = Column(String, nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "task_id": str(self.task_id) if self.task_id else None,
            "service": self.service,
            "agent_name": self.agent_name,
            "action": self.action,
            "details": self.details,
            "created_at": str(self.created_at),
        }
