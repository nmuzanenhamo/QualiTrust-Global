"""Qualification model for storing credential records."""

import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class QualificationStatus(str, enum.Enum):
    """Status of a qualification record."""

    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"
    REVOKED = "revoked"


class QualificationType(str, enum.Enum):
    """Type of qualification or certification."""

    DEGREE = "degree"
    DIPLOMA = "diploma"
    CERTIFICATE = "certificate"
    PROFESSIONAL_CERTIFICATION = "professional_certification"
    OTHER = "other"


class Qualification(Base):
    """Qualification record model."""

    __tablename__ = "qualifications"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), nullable=False, index=True)
    qualification_type = Column(Enum(QualificationType), nullable=False)
    issuing_institution = Column(String(500), nullable=False, index=True)
    holder_name = Column(String(255), nullable=False, index=True)
    holder_email = Column(String(255), nullable=True)
    holder_id_number = Column(String(100), nullable=True)
    date_issued = Column(DateTime, nullable=False)
    date_expires = Column(DateTime, nullable=True)
    registration_number = Column(String(100), nullable=True, index=True)
    serial_number = Column(String(100), nullable=True, unique=True)
    description = Column(Text, nullable=True)
    status = Column(Enum(QualificationStatus), default=QualificationStatus.PENDING, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)

    # Blockchain verification fields
    credential_hash = Column(String(64), nullable=True)
    previous_hash = Column(String(64), nullable=True)

    # Ownership
    registered_by = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    registered_by_user = relationship("User", back_populates="qualifications")
    verification_records = relationship("VerificationRecord", back_populates="qualification")
    audit_logs = relationship("AuditLog", back_populates="qualification")
