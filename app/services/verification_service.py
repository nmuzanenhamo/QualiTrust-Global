"""Verification service for qualification authenticity checks."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import (
    Qualification,
    QualificationStatus,
    User,
    VerificationMethod,
    VerificationRecord,
    VerificationResult,
)
from app.services.blockchain_service import BlockchainService


class VerificationService:
    """Service for verifying qualification authenticity."""

    @staticmethod
    def verify_qualification(
        db: Session,
        qualification_id: int,
        user: User,
        method: VerificationMethod = VerificationMethod.BLOCKCHAIN,
        notes: str | None = None,
    ) -> dict:
        """Verify a qualification and create a verification record."""
        qualification = (
            db.query(Qualification)
            .filter(Qualification.id == qualification_id, Qualification.is_deleted == False)
            .first()
        )

        if not qualification:
            raise ValueError(f"Qualification with ID {qualification_id} not found")

        blockchain_result = BlockchainService.verify_qualification(db, qualification)
        is_authentic = blockchain_result["is_authentic"]

        if is_authentic:
            qualification.status = QualificationStatus.VERIFIED
            result = VerificationResult.VERIFIED
        else:
            qualification.status = QualificationStatus.REJECTED
            result = VerificationResult.REJECTED

        db.commit()

        verification_record = VerificationRecord(
            qualification_id=qualification.id,
            verified_by=user.id,
            method=method,
            result=result,
            notes=notes or blockchain_result["message"],
            verification_hash=blockchain_result["verification_hash"],
        )
        db.add(verification_record)
        db.commit()
        db.refresh(verification_record)

        return {
            "qualification_id": qualification.id,
            "is_authentic": is_authentic,
            "result": result.value,
            "method": method.value,
            "verification_hash": blockchain_result["verification_hash"],
            "ai_confidence_score": None,
            "message": blockchain_result["message"],
            "checks": blockchain_result["checks"],
            "verified_at": verification_record.created_at,
        }

    @staticmethod
    def get_verification_history(
        db: Session,
        qualification_id: int,
    ) -> list[VerificationRecord]:
        """Get all verification records for a qualification."""
        return (
            db.query(VerificationRecord)
            .filter(VerificationRecord.qualification_id == qualification_id)
            .order_by(VerificationRecord.created_at.desc())
            .all()
        )
