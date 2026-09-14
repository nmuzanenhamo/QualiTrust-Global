"""Verification service for qualification authenticity checks."""

import json

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
    def lookup_by_serial_registration(
        db: Session,
        serial_number: str,
        registration_number: str | None = None,
    ) -> Qualification | None:
        """Find a non-deleted qualification by serial + registration number.

        If registration_number is None or empty, looks up by serial number only,
        since not all certificates include a registration number.
        """
        query = db.query(Qualification).filter(
            Qualification.serial_number == serial_number,
            Qualification.is_deleted == False,
        )
        if registration_number:
            query = query.filter(Qualification.registration_number == registration_number)
        return query.first()

    @staticmethod
    def verify_by_document(
        db: Session,
        user: User,
        method: VerificationMethod = VerificationMethod.AI_ASSISTED,
        notes: str | None = None,
        document_bytes: bytes | None = None,
        document_filename: str | None = None,
    ) -> dict:
        """Verify a credential from an uploaded document alone (employer flow).

        Extracts fields from the document (AI vision first, regex fallback),
        looks up the credential by the extracted serial/registration numbers,
        then runs the full verification with document comparison.

        Returns a dict matching DocumentVerificationResponse:
        - status "found": full verification result included
        - status "not_found": numbers extracted but no matching record — possible fraud
        - status "unable_to_verify": no serial/registration numbers could be read
        """
        from app.services.credential_extraction_service import CredentialExtractionService

        extracted = CredentialExtractionService.extract(document_bytes, document_filename or "", db=db)

        extracted_fields = {
            "holder_name": extracted.holder_name,
            "issuing_institution": extracted.issuing_institution,
            "title": extracted.title,
            "qualification_type": extracted.qualification_type,
            "grade": extracted.grade,
            "serial_number": extracted.serial_number,
            "registration_number": extracted.registration_number,
            "date_issued": extracted.date_issued,
            "holder_id_number": extracted.holder_id_number,
        }

        if not extracted.serial_number:
            return {
                "status": "unable_to_verify",
                "is_authentic": False,
                "message": "No serial number could be extracted from the document. "
                "Check the image quality, or verify using the qualification ID or serial number.",
                "extracted_fields": extracted_fields,
                "extraction_method": extracted.extraction_method,
                "qualification_found": False,
            }

        qualification = VerificationService.lookup_by_serial_registration(
            db,
            serial_number=extracted.serial_number,
            registration_number=extracted.registration_number,
        )

        if not qualification:
            return {
                "status": "not_found",
                "is_authentic": False,
                "message": f"No registered credential found with serial number "
                f"'{extracted.serial_number}'. This certificate may be fraudulent.",
                "extracted_fields": extracted_fields,
                "extraction_method": extracted.extraction_method,
                "qualification_found": False,
            }

        result = VerificationService.verify_qualification(
            db,
            qualification_id=qualification.id,
            user=user,
            method=method,
            notes=notes,
            document_bytes=document_bytes,
            document_filename=document_filename,
        )
        result.update(
            {
                "status": "found",
                "qualification_found": True,
                "extracted_fields": extracted_fields,
                "extraction_method": extracted.extraction_method,
            }
        )
        return result

    @staticmethod
    def verify_qualification(
        db: Session,
        qualification_id: int,
        user: User,
        method: VerificationMethod = VerificationMethod.BLOCKCHAIN,
        notes: str | None = None,
        document_bytes: bytes | None = None,
        document_filename: str | None = None,
    ) -> dict:
        """Verify a qualification and create a verification record.

        Verification confirms that the credential record exists in the database
        and displays the full confirmed details (title, institution, holder,
        grade, dates, serial/reg numbers).

        The blockchain hash chain checks are included as informational integrity
        checks but do not determine pass/fail — the record's existence in the
        database is the primary verification.

        For ai_assisted and automated methods, also runs AI fraud analysis.

        If document_bytes is provided, extracts text from the uploaded document
        and compares it against the registered data (and the stored document
        if one exists) to detect forged certificates with matching serial/reg
        numbers but different qualification details.
        """
        qualification = (
            db.query(Qualification)
            .filter(Qualification.id == qualification_id, Qualification.is_deleted == False)
            .first()
        )

        if not qualification:
            raise ValueError(f"Qualification with ID {qualification_id} not found")

        # The record exists in the database — that's the primary verification
        is_authentic = True

        # Blockchain checks are informational (shown but don't determine pass/fail)
        blockchain_result = BlockchainService.verify_qualification(db, qualification)

        ai_analysis = None
        ai_confidence_score = None
        document_analysis = None

        if method in (VerificationMethod.AI_ASSISTED, VerificationMethod.AUTOMATED):
            from app.services.ai_service import AIService

            ai_analysis = AIService._heuristic_analysis(qualification)
            ai_confidence_score = ai_analysis.get("confidence_score")

            if "REJECT" in ai_analysis.get("recommendation", "").upper():
                overall_result = VerificationResult.REJECTED
                is_authentic = False
            elif "REVIEW" in ai_analysis.get("recommendation", "").upper():
                overall_result = VerificationResult.INCONCLUSIVE
            else:
                overall_result = VerificationResult.VERIFIED
        else:
            overall_result = VerificationResult.VERIFIED

        # Document comparison (works for any method when a document is uploaded)
        if document_bytes:
            from app.services.document_comparison_service import DocumentComparisonService
            from app.services.document_service import DocumentService

            extracted_text = DocumentService.extract_text(document_bytes, document_filename or "")

            # Compare uploaded document against registered data
            data_match = DocumentComparisonService.compare_document_to_qualification(extracted_text, qualification)

            # If the registered qualification also has a stored document, compare the two documents
            doc_vs_doc = None
            if qualification.document_path:
                import os

                uploads_dir = os.path.join(
                    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))),
                    "uploads",
                )
                stored_path = os.path.join(uploads_dir, os.path.basename(qualification.document_path))
                if os.path.exists(stored_path):
                    with open(stored_path, "rb") as f:
                        stored_bytes = f.read()
                    stored_text = DocumentService.extract_text(stored_bytes, qualification.document_path)
                    if stored_text.strip() and extracted_text.strip():
                        doc_vs_doc = DocumentComparisonService.compare_two_documents(stored_text, extracted_text)

            document_analysis = {
                "data_match": {
                    "match_score": data_match.match_score,
                    "checks": data_match.checks,
                    "recommendation": data_match.recommendation,
                    "summary": data_match.summary,
                },
                "document_vs_document": {
                    "match_score": doc_vs_doc.match_score,
                    "checks": doc_vs_doc.checks,
                    "recommendation": doc_vs_doc.recommendation,
                    "summary": doc_vs_doc.summary,
                }
                if doc_vs_doc
                else None,
                "extracted_text_preview": extracted_text[:500],
            }

            # Factor document analysis into the overall result
            if data_match.recommendation == "REJECT":
                if overall_result == VerificationResult.VERIFIED:
                    overall_result = VerificationResult.REJECTED
                    is_authentic = False
            elif data_match.recommendation == "REVIEW":
                if overall_result == VerificationResult.VERIFIED:
                    overall_result = VerificationResult.INCONCLUSIVE

            if doc_vs_doc and doc_vs_doc.recommendation == "REJECT":
                if overall_result == VerificationResult.VERIFIED:
                    overall_result = VerificationResult.REJECTED
                    is_authentic = False

        if overall_result == VerificationResult.VERIFIED:
            qualification.status = QualificationStatus.VERIFIED
        elif overall_result == VerificationResult.REJECTED:
            qualification.status = QualificationStatus.REJECTED

        db.commit()

        record_notes = notes or "Credential record found in database"
        if ai_analysis:
            record_notes = json.dumps(ai_analysis, indent=2)

        verification_record = VerificationRecord(
            qualification_id=qualification.id,
            verified_by=user.id,
            method=method,
            result=overall_result,
            notes=record_notes,
            verification_hash=blockchain_result["verification_hash"],
            ai_confidence_score=ai_confidence_score,
        )
        db.add(verification_record)
        db.commit()
        db.refresh(verification_record)

        message = "Credential verified — record found in database"
        if ai_analysis and ai_analysis.get("anomalies"):
            message += f" | AI: {ai_analysis['recommendation']}"
        if document_analysis:
            message += f" | Document: {document_analysis['data_match']['recommendation']}"

        return {
            "qualification_id": qualification.id,
            "is_authentic": is_authentic,
            "result": overall_result.value,
            "method": method.value,
            "verification_hash": blockchain_result["verification_hash"],
            "ai_confidence_score": ai_confidence_score,
            "message": message,
            "checks": blockchain_result["checks"],
            "ai_analysis": ai_analysis,
            "document_analysis": document_analysis,
            "qualification": {
                "id": qualification.id,
                "title": qualification.title,
                "qualification_type": qualification.qualification_type.value
                if hasattr(qualification.qualification_type, "value")
                else str(qualification.qualification_type),
                "issuing_institution": qualification.issuing_institution,
                "holder_name": qualification.holder_name,
                "holder_email": qualification.holder_email,
                "holder_id_number": qualification.holder_id_number,
                "grade": qualification.grade,
                "date_issued": qualification.date_issued.isoformat() if qualification.date_issued else None,
                "registration_number": qualification.registration_number,
                "serial_number": qualification.serial_number,
                "status": qualification.status.value if qualification.status else None,
                "credential_hash": qualification.credential_hash,
                "description": qualification.description,
            },
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
