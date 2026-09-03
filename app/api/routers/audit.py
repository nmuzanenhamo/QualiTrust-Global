"""Audit log router for querying audit history."""

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.models import User
from app.schemas.audit import AuditLogResponse, AuditLogSearchResult
from app.services.audit_service import AuditService

router = APIRouter()


@router.get("/", response_model=AuditLogSearchResult)
def search_audit_logs(
    user_id: int | None = Query(None, description="Filter by user ID"),
    action: str | None = Query(None, description="Filter by action type"),
    entity_type: str | None = Query(None, description="Filter by entity type"),
    entity_id: int | None = Query(None, description="Filter by entity ID"),
    qualification_id: int | None = Query(None, description="Filter by qualification ID"),
    start_date: str | None = Query(None, description="Filter from date (ISO format)"),
    end_date: str | None = Query(None, description="Filter to date (ISO format)"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search and retrieve audit log entries with filters and pagination."""
    return AuditService.search_audit_logs(
        db,
        user_id=user_id,
        action=action,
        entity_type=entity_type,
        entity_id=entity_id,
        qualification_id=qualification_id,
        start_date=start_date,
        end_date=end_date,
        page=page,
        page_size=page_size,
    )


@router.get("/{log_id}", response_model=AuditLogResponse)
def get_audit_log(
    log_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a specific audit log entry by ID."""
    log = AuditService.get_audit_log_by_id(db, log_id)
    if not log:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Audit log with ID {log_id} not found",
        )
    return log
