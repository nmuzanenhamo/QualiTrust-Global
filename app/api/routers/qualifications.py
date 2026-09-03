"""Qualification CRUD router."""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_verifier
from app.models import User
from app.schemas.qualification import (
    QualificationCreate,
    QualificationResponse,
    QualificationSearchResult,
    QualificationUpdate,
)
from app.services.qualification_service import QualificationService

router = APIRouter()


@router.get("/", response_model=QualificationSearchResult)
def search_qualifications(
    query: str | None = Query(None, description="Search by title, holder name, or registration number"),
    qualification_type: str | None = Query(None, description="Filter by qualification type"),
    status: str | None = Query(None, description="Filter by status"),
    issuing_institution: str | None = Query(None, description="Filter by issuing institution"),
    holder_name: str | None = Query(None, description="Filter by holder name"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Search and retrieve qualification records with pagination and filters."""
    return QualificationService.search_qualifications(
        db,
        query=query,
        qualification_type=qualification_type,
        status=status,
        issuing_institution=issuing_institution,
        holder_name=holder_name,
        page=page,
        page_size=page_size,
    )


@router.post("/", response_model=QualificationResponse, status_code=status.HTTP_201_CREATED)
def create_qualification(
    qualification_data: QualificationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verifier),
):
    """Register a new qualification. Requires verifier or admin role."""
    return QualificationService.create_qualification(db, qualification_data, current_user)


@router.get("/{qualification_id}", response_model=QualificationResponse)
def get_qualification(
    qualification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieve a specific qualification by ID."""
    qualification = QualificationService.get_qualification(db, qualification_id)
    if not qualification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Qualification with ID {qualification_id} not found",
        )
    return qualification


@router.put("/{qualification_id}", response_model=QualificationResponse)
def update_qualification(
    qualification_id: int,
    update_data: QualificationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verifier),
):
    """Update a qualification record. Requires verifier or admin role."""
    qualification = QualificationService.update_qualification(db, qualification_id, update_data)
    if not qualification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Qualification with ID {qualification_id} not found",
        )
    return qualification


@router.delete("/{qualification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_qualification(
    qualification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verifier),
):
    """Soft delete a qualification. Requires verifier or admin role."""
    deleted = QualificationService.soft_delete_qualification(db, qualification_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Qualification with ID {qualification_id} not found",
        )
