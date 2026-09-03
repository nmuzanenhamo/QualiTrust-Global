"""Verification router for qualification authenticity checks."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_verifier
from app.models import User, VerificationMethod
from app.schemas.verification import VerificationRecordResponse, VerificationResultResponse
from app.services.verification_service import VerificationService

router = APIRouter()


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
    """Verify the authenticity of a qualification using blockchain hash verification."""
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
