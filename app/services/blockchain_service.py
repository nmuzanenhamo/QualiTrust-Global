"""Blockchain service for credential verification using SHA-256 hash chaining.

This module implements a lightweight blockchain mechanism where each
qualification credential is hashed and chained to the previous credential's
hash, creating a tamper-evident ledger of records.
"""

import hashlib
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Qualification, VerificationRecord


class BlockchainService:
    """Service for blockchain-based credential verification."""

    @staticmethod
    def compute_credential_hash(qualification: Qualification) -> str:
        """Compute SHA-256 hash of the qualification credential data."""
        credential_data = {
            "id": qualification.id,
            "title": qualification.title,
            "qualification_type": qualification.qualification_type.value
            if hasattr(qualification.qualification_type, "value")
            else str(qualification.qualification_type),
            "issuing_institution": qualification.issuing_institution,
            "holder_name": qualification.holder_name,
            "holder_email": qualification.holder_email or "",
            "holder_id_number": qualification.holder_id_number or "",
            "date_issued": qualification.date_issued.isoformat() if qualification.date_issued else "",
            "date_expires": qualification.date_expires.isoformat() if qualification.date_expires else "",
            "registration_number": qualification.registration_number or "",
            "serial_number": qualification.serial_number or "",
        }
        data_string = json.dumps(credential_data, sort_keys=True)
        return hashlib.sha256(data_string.encode("utf-8")).hexdigest()

    @staticmethod
    def get_previous_hash(db: Session) -> str:
        """Get the hash of the most recently registered qualification."""
        last_qual = (
            db.query(Qualification)
            .filter(Qualification.credential_hash.isnot(None))
            .order_by(Qualification.id.desc())
            .first()
        )
        if last_qual:
            return last_qual.credential_hash
        return "0" * 64

    @staticmethod
    def assign_hash(db: Session, qualification: Qualification) -> Qualification:
        """Assign a credential hash and previous hash to a qualification."""
        previous_hash = BlockchainService.get_previous_hash(db)
        qualification.previous_hash = previous_hash
        qualification.credential_hash = BlockchainService.compute_credential_hash(qualification)
        db.commit()
        db.refresh(qualification)
        return qualification

    @staticmethod
    def verify_chain_integrity(db: Session, qualification: Qualification) -> bool:
        """Verify that a qualification's hash chain is intact."""
        stored_hash = qualification.credential_hash
        if not stored_hash:
            return False

        recomputed_hash = BlockchainService.compute_credential_hash(qualification)
        if recomputed_hash != stored_hash:
            return False

        if qualification.id > 1:
            prev_qual = (
                db.query(Qualification)
                .filter(Qualification.id == qualification.id - 1)
                .first()
            )
            if prev_qual and prev_qual.credential_hash != qualification.previous_hash:
                return False

        return True

    @staticmethod
    def verify_qualification(db: Session, qualification: Qualification) -> dict:
        """Verify a qualification and return verification result."""
        chain_valid = BlockchainService.verify_chain_integrity(db, qualification)

        checks = {
            "has_hash": qualification.credential_hash is not None,
            "hash_valid": chain_valid,
            "has_serial": qualification.serial_number is not None,
            "has_registration": qualification.registration_number is not None,
            "not_expired": (
                qualification.date_expires is None
                or qualification.date_expires > datetime.now(timezone.utc)
            ),
            "not_revoked": qualification.status.value != "revoked" if qualification.status else False,
        }

        all_passed = all(checks.values())

        result = {
            "is_authentic": all_passed,
            "checks": checks,
            "verification_hash": qualification.credential_hash,
            "message": "Qualification verified successfully" if all_passed else "Qualification verification failed",
        }

        return result
