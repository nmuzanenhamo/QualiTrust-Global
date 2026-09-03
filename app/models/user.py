"""User model for authentication and authorization."""

import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, Integer, String, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class UserRole(str, enum.Enum):
    """User roles for role-based access control."""

    ADMIN = "admin"
    VERIFIER = "verifier"
    VIEWER = "viewer"


class User(Base):
    """User model for system authentication."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(255), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.VIEWER, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    qualifications = relationship("Qualification", back_populates="registered_by_user")
    verification_records = relationship("VerificationRecord", back_populates="verified_by_user")
    audit_logs = relationship("AuditLog", back_populates="user")
