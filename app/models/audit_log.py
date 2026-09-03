"""Audit log model for immutable audit trail."""

import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class AuditAction(str, enum.Enum):
    """Types of actions that can be audited."""

    CREATE = "create"
    READ = "read"
    UPDATE = "update"
    DELETE = "delete"
    VERIFY = "verify"
    LOGIN = "login"
    LOGOUT = "logout"
    AI_ANALYSIS = "ai_analysis"


class AuditLog(Base):
    """Immutable audit log entry for all system actions."""

    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    qualification_id = Column(Integer, ForeignKey("qualifications.id"), nullable=True, index=True)
    action = Column(Enum(AuditAction), nullable=False)
    entity_type = Column(String(50), nullable=False)
    entity_id = Column(Integer, nullable=True)
    description = Column(Text, nullable=False)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(String(500), nullable=True)
    old_values = Column(Text, nullable=True)
    new_values = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="audit_logs")
    qualification = relationship("Qualification", back_populates="audit_logs")
