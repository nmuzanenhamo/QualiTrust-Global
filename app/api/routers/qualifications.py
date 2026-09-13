"""Qualification CRUD router."""

import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import get_current_user, require_verifier
from app.models import AuditAction, User
from app.schemas.qualification import (
    QualificationCreate,
    QualificationResponse,
    QualificationSearchResult,
    QualificationUpdate,
)
from app.schemas.verification import CredentialLookupResponse, ExtractedCredentialData
from app.services.audit_service import AuditService
from app.services.credential_extraction_service import CredentialExtractionService
from app.services.qualification_service import QualificationService
from app.services.verification_service import VerificationService

router = APIRouter()

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), "uploads")
ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


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
    qualification = QualificationService.create_qualification(db, qualification_data, current_user)
    AuditService.log_action(
        db,
        user_id=current_user.id,
        action=AuditAction.CREATE,
        entity_type="qualification",
        entity_id=qualification.id,
        qualification_id=qualification.id,
        description=f"Registered qualification '{qualification.title}' for {qualification.holder_name}",
        new_values={"title": qualification.title, "holder_name": qualification.holder_name},
    )
    return qualification


@router.get("/lookup", response_model=CredentialLookupResponse)
def lookup_credential(
    serial_number: str = Query(..., description="Serial number on the transcript"),
    registration_number: str | None = Query(None, description="Registration number on the transcript (optional)"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Look up a qualification by serial + registration number.

    Allows external verifiers to find a credential using the numbers printed
    on a transcript or certificate without knowing the internal database ID.
    Registration number is optional — not all certificates include one.
    """
    qualification = VerificationService.lookup_by_serial_registration(db, serial_number, registration_number)
    if not qualification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No credential found with the provided serial and registration numbers.",
        )
    return qualification


@router.post("/extract", response_model=ExtractedCredentialData)
def extract_credential_data(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    """Upload a certificate/transcript and extract qualification data via OCR.

    Accepts PDF, JPG, PNG, GIF, BMP, and WebP files up to 10 MB.
    Extracts text using OCR (Tesseract for images, pdfplumber for PDFs),
    then parses the text to identify:

    - Holder name
    - Issuing institution
    - Qualification title
    - Qualification type
    - Grade / class of degree (e.g. First Class, Upper Second (2.1))
    - Serial number
    - Registration number
    - Date issued
    - Holder ID number

    Returns the extracted data for review before registering the qualification.
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = file.file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 10 MB.",
        )

    extracted = CredentialExtractionService.extract(content, file.filename or "")

    return ExtractedCredentialData(
        holder_name=extracted.holder_name,
        issuing_institution=extracted.issuing_institution,
        title=extracted.title,
        qualification_type=extracted.qualification_type,
        grade=extracted.grade,
        serial_number=extracted.serial_number,
        registration_number=extracted.registration_number,
        date_issued=extracted.date_issued,
        holder_id_number=extracted.holder_id_number,
        raw_text=extracted.raw_text[:2000] if extracted.raw_text else None,
        confidence=extracted.confidence,
    )


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
    old = QualificationService.get_qualification(db, qualification_id)
    qualification = QualificationService.update_qualification(db, qualification_id, update_data)
    if not qualification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Qualification with ID {qualification_id} not found",
        )
    AuditService.log_action(
        db,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="qualification",
        entity_id=qualification.id,
        qualification_id=qualification.id,
        description=f"Updated qualification '{qualification.title}'",
        old_values={"title": old.title} if old else None,
        new_values={"title": qualification.title},
    )
    return qualification


@router.delete("/{qualification_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_qualification(
    qualification_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verifier),
):
    """Soft delete a qualification. Requires verifier or admin role."""
    qual = QualificationService.get_qualification(db, qualification_id)
    deleted = QualificationService.soft_delete_qualification(db, qualification_id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Qualification with ID {qualification_id} not found",
        )
    AuditService.log_action(
        db,
        user_id=current_user.id,
        action=AuditAction.DELETE,
        entity_type="qualification",
        entity_id=qualification_id,
        qualification_id=qualification_id,
        description=f"Deleted qualification '{qual.title if qual else qualification_id}'",
    )


@router.post("/{qualification_id}/document", response_model=QualificationResponse)
def upload_document(
    qualification_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_verifier),
):
    """Upload a certificate/transcript document for a qualification.

    Accepts PDF, JPG, PNG, GIF, BMP, and WebP files up to 10 MB.
    Replaces any existing document.
    """
    qualification = QualificationService.get_qualification(db, qualification_id)
    if not qualification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Qualification with ID {qualification_id} not found",
        )

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Accepted: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    content = file.file.read(MAX_FILE_SIZE + 1)
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File too large. Maximum size is 10 MB.",
        )

    os.makedirs(UPLOAD_DIR, exist_ok=True)

    if qualification.document_path:
        old_path = os.path.join(UPLOAD_DIR, os.path.basename(qualification.document_path))
        if os.path.exists(old_path):
            os.remove(old_path)

    safe_name = f"qual_{qualification_id}_{uuid.uuid4().hex[:8]}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_name)
    with open(file_path, "wb") as f:
        f.write(content)

    qualification.document_path = f"/uploads/{safe_name}"
    db.commit()
    db.refresh(qualification)

    AuditService.log_action(
        db,
        user_id=current_user.id,
        action=AuditAction.UPDATE,
        entity_type="qualification",
        entity_id=qualification.id,
        qualification_id=qualification.id,
        description=f"Uploaded document for qualification '{qualification.title}'",
    )

    return qualification
