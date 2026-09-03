"""Unit tests for the BlockchainService."""

import hashlib
import json

from app.models import Qualification, QualificationStatus, QualificationType
from app.services.blockchain_service import BlockchainService


class TestBlockchainService:
    """Tests for BlockchainService methods."""

    def test_compute_credential_hash(self, db_session, admin_user):
        """Test that credential hash is computed correctly."""
        qual = Qualification(
            title="Test Degree",
            qualification_type=QualificationType.DEGREE,
            issuing_institution="Test University",
            holder_name="Test Holder",
            holder_email="holder@test.com",
            holder_id_number="ID123",
            date_issued="2020-01-01T00:00:00",
            registration_number="REG001",
            serial_number="SN001",
            status=QualificationStatus.PENDING,
            registered_by=admin_user.id,
        )
        db_session.add(qual)
        db_session.commit()
        db_session.refresh(qual)

        hash_value = BlockchainService.compute_credential_hash(qual)
        assert len(hash_value) == 64
        assert all(c in "0123456789abcdef" for c in hash_value)

    def test_assign_hash(self, db_session, admin_user):
        """Test that hash and previous hash are assigned."""
        qual = Qualification(
            title="Test Degree 2",
            qualification_type=QualificationType.DEGREE,
            issuing_institution="Test University",
            holder_name="Test Holder 2",
            date_issued="2020-01-01T00:00:00",
            registration_number="REG002",
            serial_number="SN002",
            status=QualificationStatus.PENDING,
            registered_by=admin_user.id,
        )
        db_session.add(qual)
        db_session.commit()
        db_session.refresh(qual)

        BlockchainService.assign_hash(db_session, qual)
        assert qual.credential_hash is not None
        assert qual.previous_hash is not None
        assert len(qual.credential_hash) == 64

    def test_verify_chain_integrity_valid(self, db_session, admin_user):
        """Test that a valid chain passes integrity check."""
        qual = Qualification(
            title="Valid Degree",
            qualification_type=QualificationType.DEGREE,
            issuing_institution="Valid University",
            holder_name="Valid Holder",
            date_issued="2020-01-01T00:00:00",
            registration_number="REG003",
            serial_number="SN003",
            status=QualificationStatus.VERIFIED,
            registered_by=admin_user.id,
        )
        db_session.add(qual)
        db_session.commit()
        db_session.refresh(qual)

        BlockchainService.assign_hash(db_session, qual)
        is_valid = BlockchainService.verify_chain_integrity(db_session, qual)
        assert is_valid is True

    def test_verify_chain_integrity_tampered(self, db_session, admin_user):
        """Test that a tampered credential fails integrity check."""
        qual = Qualification(
            title="Tampered Degree",
            qualification_type=QualificationType.DEGREE,
            issuing_institution="Test University",
            holder_name="Tampered Holder",
            date_issued="2020-01-01T00:00:00",
            registration_number="REG004",
            serial_number="SN004",
            status=QualificationStatus.VERIFIED,
            registered_by=admin_user.id,
        )
        db_session.add(qual)
        db_session.commit()
        db_session.refresh(qual)

        BlockchainService.assign_hash(db_session, qual)
        qual.title = "Tampered Title"
        db_session.commit()

        is_valid = BlockchainService.verify_chain_integrity(db_session, qual)
        assert is_valid is False

    def test_verify_qualification_result(self, db_session, admin_user):
        """Test the full verification result."""
        qual = Qualification(
            title="Verify Me",
            qualification_type=QualificationType.DEGREE,
            issuing_institution="Verify University",
            holder_name="Verify Holder",
            date_issued="2020-01-01T00:00:00",
            registration_number="REG005",
            serial_number="SN005",
            status=QualificationStatus.PENDING,
            registered_by=admin_user.id,
        )
        db_session.add(qual)
        db_session.commit()
        db_session.refresh(qual)

        BlockchainService.assign_hash(db_session, qual)
        result = BlockchainService.verify_qualification(db_session, qual)
        assert "is_authentic" in result
        assert "checks" in result
        assert "verification_hash" in result
        assert "message" in result
