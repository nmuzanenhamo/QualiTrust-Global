"""Verification record model for tracking verification activities."""

import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class VerificationMethod(str, enum.Enum):
    """Method used to verify a qualification."""

    MANUAL = "manual"
    BLOCKCHAIN = "blockchain"
    AI_ASSISTED = "ai_assisted"
    AUTOMATED = "automated"


class VerificationResult(str, enum.Enum):
    """Result of a verification attempt."""

    VERIFIED = "verified"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"


class VerificationRecord(Base):
    """Record of a single verification attempt."""

    __tablename__ = "verification_records"

    id = Column(Integer, primary_key=True, index=True)
    qualification_id = Column(Integer, ForeignKey("qualifications.id"), nullable=False, index=True)
    verified_by = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    method = Column(Enum(VerificationMethod), default=VerificationMethod.MANUAL, nullable=False)
    result = Column(Enum(VerificationResult), nullable=False)
    notes = Column(Text, nullable=True)
    verification_hash = Column(String(64), nullable=True)
    ai_confidence_score = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    qualification = relationship("Qualification", back_populates="verification_records")
    verified_by_user = relationship("User", back_populates="verification_records")
