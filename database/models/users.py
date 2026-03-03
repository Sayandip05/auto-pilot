"""
database/models/users.py
SQLAlchemy model for the users table.
"""

from sqlalchemy import Column, String, BigInteger, JSON, TIMESTAMP, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, server_default=text("uuid_generate_v4()"))
    telegram_id = Column(BigInteger, unique=True, nullable=True)
    discord_id = Column(String, unique=True, nullable=True)
    email = Column(String, unique=True, nullable=True)
    api_key = Column(String, unique=True, nullable=False)
    preferences = Column(JSON, default=dict)
    created_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))
    updated_at = Column(TIMESTAMP(timezone=True), server_default=text("NOW()"))

    def to_dict(self) -> dict:
        return {
            "id": str(self.id),
            "telegram_id": self.telegram_id,
            "discord_id": self.discord_id,
            "email": self.email,
            "preferences": self.preferences or {},
            "created_at": str(self.created_at),
        }
