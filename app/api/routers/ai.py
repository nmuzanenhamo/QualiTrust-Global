"""AI verification assistant router."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_verifier
from app.models import AuditAction, User
from app.services.ai_service import AIService
from app.services.audit_service import AuditService

router = APIRouter()


@router.post("/analyze/{qualification_id}")
async def analyze_credential(
    qualification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verifier),
):
    """Analyze a qualification credential using AI for fraud detection and anomaly identification."""
    try:
        result = await AIService.analyze_credential(db, qualification_id, current_user)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )

    AuditService.log_action(
        db,
        user_id=current_user.id,
        action=AuditAction.AI_ANALYSIS,
        entity_type="qualification",
        entity_id=qualification_id,
        qualification_id=qualification_id,
        description=f"AI analysis: risk={result.get('risk_score', 0)}, result={result.get('result', 'unknown')}",
    )

    return result
