"""Verification router for qualification authenticity checks."""

import os

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_verifier
from app.models import AuditAction, User, VerificationMethod
from app.schemas.verification import VerificationRecordResponse, VerificationResultResponse
from app.services.audit_service import AuditService
from app.services.verification_service import VerificationService

router = APIRouter()

MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


@router.post(
    "/{qualification_id}/verify",
    response_model=VerificationResultResponse,
)
def verify_qualification(
    qualification_id: int,
    method: str = "blockchain",
    notes: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verifier),
):
    """Verify the authenticity of a qualification.

    - **blockchain**: Runs 6 SHA-256 hash chain integrity checks.
    - **manual**: Same blockchain checks, recorded as human-reviewed.
    - **ai_assisted**: Blockchain checks + AI fraud analysis (risk score, anomalies, recommendation).
    - **automated**: Blockchain checks + AI fraud analysis (fully automated, no human review).
    """
    try:
        verification_method = VerificationMethod(method)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification method. Use: {[m.value for m in VerificationMethod]}",
        )

    try:
        result = VerificationService.verify_qualification(
            db,
            qualification_id=qualification_id,
            user=current_user,
            method=verification_method,
            notes=notes,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    AuditService.log_action(
        db,
        user_id=current_user.id,
        action=AuditAction.VERIFY,
        entity_type="qualification",
        entity_id=qualification_id,
        qualification_id=qualification_id,
        description=f"Verification via {verification_method.value}: result={result['result']}",
    )

    return result


@router.post(
    "/{qualification_id}/verify-with-document",
    response_model=VerificationResultResponse,
)
def verify_qualification_with_document(
    qualification_id: int,
    method: str = Form("ai_assisted"),
    notes: str | None = Form(None),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verifier),
):
    """Verify a qualification by uploading a document (certificate/transcript) for AI comparison.

    The system extracts text from the uploaded document and compares it against:
    1. The registered qualification data (holder name, institution, title, serial, reg)
    2. The stored document uploaded during registration (if one exists)

    This detects forged certificates that use the same serial and registration numbers
    but have different qualification details.

    - **blockchain/manual**: Blockchain checks + document comparison only.
    - **ai_assisted/automated**: Blockchain checks + AI fraud analysis + document comparison.
    """
    try:
        verification_method = VerificationMethod(method)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid verification method. Use: {[m.value for m in VerificationMethod]}",
        )

    content = file.file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 10 MB.",
        )

    try:
        result = VerificationService.verify_qualification(
            db,
            qualification_id=qualification_id,
            user=current_user,
            method=verification_method,
            notes=notes,
            document_bytes=content,
            document_filename=file.filename,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    AuditService.log_action(
        db,
        user_id=current_user.id,
        action=AuditAction.VERIFY,
        entity_type="qualification",
        entity_id=qualification_id,
        qualification_id=qualification_id,
        description=f"Verification with document via {verification_method.value}: result={result['result']}",
    )

    return result


@router.get(
    "/{qualification_id}/verifications",
    response_model=list[VerificationRecordResponse],
)
def get_verification_history(
    qualification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verifier),
):
    """Get the verification history for a qualification."""
    history = VerificationService.get_verification_history(db, qualification_id)
    return history
