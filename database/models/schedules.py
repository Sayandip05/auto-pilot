"""
database/models/schedules.py
SQLAlchemy model for scheduled workflows and price tracks.
"""

from sqlalchemy import Column, String, Boolean, Numeric, JSON, TIMESTAMP, ForeignKey, text
from sqlalchemy.dialects.postgresql import UUID
from database.models.users import Base


class Schedule(Base):
    __tablename__ = "schedules"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    workflow_type = Column(String, nullable=False)
    cron_expression = Column(String, nullable=True)
    next_run_at = Column(TIMESTAMP(timezone=True), nullable=False)
    last_run_at = Column(TIMESTAMP(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True)
    config = Column(JSON, default=dict)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "workflow_type": self.workflow_type,
            "cron_expression": self.cron_expression,
            "next_run_at": str(self.next_run_at),
            "last_run_at": str(self.last_run_at) if self.last_run_at else None,
            "is_active": self.is_active,
            "config": self.config,
        }


class PriceTrack(Base):
    __tablename__ = "price_tracks"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    schedule_id = Column(UUID(as_uuid=True), ForeignKey("schedules.id", ondelete="SET NULL"), nullable=True)
    product_url = Column(String, nullable=False)
    product_name = Column(String, nullable=True)
    baseline_price = Column(Numeric(10, 2), nullable=True)
    current_price = Column(Numeric(10, 2), nullable=True)
    alert_threshold = Column(Numeric(10, 2), nullable=True)
    is_active = Column(Boolean, default=True)
    last_checked_at = Column(TIMESTAMP(timezone=True), nullable=True)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "product_url": self.product_url,
            "product_name": self.product_name,
            "baseline_price": float(self.baseline_price) if self.baseline_price else None,
            "current_price": float(self.current_price) if self.current_price else None,
            "alert_threshold": float(self.alert_threshold) if self.alert_threshold else None,
            "is_active": self.is_active,
            "last_checked_at": str(self.last_checked_at) if self.last_checked_at else None,
        }
