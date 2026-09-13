"""Unit tests for VerificationService."""

import pytest

from app.models import QualificationStatus, QualificationType, VerificationMethod, VerificationResult
from app.schemas.qualification import QualificationCreate
from app.services.qualification_service import QualificationService
from app.services.verification_service import VerificationService


class TestLookupBySerialRegistration:
    """Tests for lookup_by_serial_registration."""

    def test_lookup_by_serial_only(self, db_session, admin_user, sample_qualification_data):
        data = QualificationCreate(**sample_qualification_data)
        QualificationService.create_qualification(db_session, data, admin_user)

        result = VerificationService.lookup_by_serial_registration(
            db_session, serial_number=sample_qualification_data["serial_number"]
        )
        assert result is not None
        assert result.serial_number == sample_qualification_data["serial_number"]

    def test_lookup_by_serial_and_registration(self, db_session, admin_user, sample_qualification_data):
        data = QualificationCreate(**sample_qualification_data)
        QualificationService.create_qualification(db_session, data, admin_user)

        result = VerificationService.lookup_by_serial_registration(
            db_session,
            serial_number=sample_qualification_data["serial_number"],
            registration_number=sample_qualification_data["registration_number"],
        )
        assert result is not None

    def test_lookup_not_found(self, db_session):
        result = VerificationService.lookup_by_serial_registration(db_session, "NONEXISTENT")
        assert result is None

    def test_lookup_empty_registration_uses_serial_only(self, db_session, admin_user, sample_qualification_data):
        data = QualificationCreate(**sample_qualification_data)
        QualificationService.create_qualification(db_session, data, admin_user)

        result = VerificationService.lookup_by_serial_registration(
            db_session,
            serial_number=sample_qualification_data["serial_number"],
            registration_number="",
        )
        assert result is not None


class TestVerifyQualification:
    """Tests for verify_qualification."""

    def test_verify_blockchain_method(self, db_session, admin_user, sample_qualification_data):
        data = QualificationCreate(**sample_qualification_data)
        qual = QualificationService.create_qualification(db_session, data, admin_user)

        result = VerificationService.verify_qualification(
            db_session,
            qualification_id=qual.id,
            user=admin_user,
            method=VerificationMethod.BLOCKCHAIN,
        )
        assert result["is_authentic"] is True
        assert result["result"] == "verified"
        assert result["qualification_id"] == qual.id
        assert "verification_hash" in result
        assert result["ai_analysis"] is None

    def test_verify_ai_assisted_method(self, db_session, admin_user, sample_qualification_data):
        data = QualificationCreate(**sample_qualification_data)
        qual = QualificationService.create_qualification(db_session, data, admin_user)

        result = VerificationService.verify_qualification(
            db_session,
            qualification_id=qual.id,
            user=admin_user,
            method=VerificationMethod.AI_ASSISTED,
        )
        assert result["ai_analysis"] is not None
        assert "ai_confidence_score" in result
        assert result["result"] in ("verified", "inconclusive", "rejected")

    def test_verify_not_found_raises(self, db_session, admin_user):
        with pytest.raises(ValueError, match="not found"):
            VerificationService.verify_qualification(
                db_session,
                qualification_id=99999,
                user=admin_user,
            )

    def test_verify_returns_qualification_details(self, db_session, admin_user, sample_qualification_data):
        data = QualificationCreate(**sample_qualification_data)
        qual = QualificationService.create_qualification(db_session, data, admin_user)

        result = VerificationService.verify_qualification(
            db_session,
            qualification_id=qual.id,
            user=admin_user,
        )
        assert "qualification" in result
        assert result["qualification"]["title"] == sample_qualification_data["title"]
        assert result["qualification"]["holder_name"] == sample_qualification_data["holder_name"]
        assert result["qualification"]["serial_number"] == sample_qualification_data["serial_number"]

    def test_verify_with_document_bytes(self, db_session, admin_user, sample_qualification_data):
        data = QualificationCreate(**sample_qualification_data)
        qual = QualificationService.create_qualification(db_session, data, admin_user)

        # Create a simple text "document" that matches the qualification data
        doc_text = f"""
        {sample_qualification_data['holder_name']}
        {sample_qualification_data['issuing_institution']}
        {sample_qualification_data['title']}
        {sample_qualification_data['serial_number']}
        {sample_qualification_data['registration_number']}
        """
        doc_bytes = doc_text.encode("utf-8")

        result = VerificationService.verify_qualification(
            db_session,
            qualification_id=qual.id,
            user=admin_user,
            document_bytes=doc_bytes,
            document_filename="cert.txt",
        )
        assert "document_analysis" in result
        assert result["document_analysis"] is not None
        assert "data_match" in result["document_analysis"]

    def test_verify_updates_status_to_verified(self, db_session, admin_user, sample_qualification_data):
        data = QualificationCreate(**sample_qualification_data)
        qual = QualificationService.create_qualification(db_session, data, admin_user)

        VerificationService.verify_qualification(
            db_session,
            qualification_id=qual.id,
            user=admin_user,
        )
        db_session.refresh(qual)
        assert qual.status == QualificationStatus.VERIFIED


class TestGetVerificationHistory:
    """Tests for get_verification_history."""

    def test_empty_history(self, db_session, admin_user, sample_qualification_data):
        data = QualificationCreate(**sample_qualification_data)
        qual = QualificationService.create_qualification(db_session, data, admin_user)

        history = VerificationService.get_verification_history(db_session, qual.id)
        assert history == []

    def test_history_after_verification(self, db_session, admin_user, sample_qualification_data):
        data = QualificationCreate(**sample_qualification_data)
        qual = QualificationService.create_qualification(db_session, data, admin_user)

        VerificationService.verify_qualification(
            db_session,
            qualification_id=qual.id,
            user=admin_user,
        )

        history = VerificationService.get_verification_history(db_session, qual.id)
        assert len(history) == 1
        assert history[0].qualification_id == qual.id

    def test_multiple_verifications(self, db_session, admin_user, sample_qualification_data):
        data = QualificationCreate(**sample_qualification_data)
        qual = QualificationService.create_qualification(db_session, data, admin_user)

        for _ in range(3):
            VerificationService.verify_qualification(
                db_session,
                qualification_id=qual.id,
                user=admin_user,
            )

        history = VerificationService.get_verification_history(db_session, qual.id)
        assert len(history) == 3
