"""Pydantic schemas for VerificationRecord model."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class VerificationRecordCreate(BaseModel):
    """Schema for creating a verification record."""

    method: str = "manual"
    notes: str | None = None


class VerificationRecordResponse(BaseModel):
    """Schema for verification record response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    qualification_id: int
    verified_by: int
    method: str
    result: str
    notes: str | None = None
    verification_hash: str | None = None
    ai_confidence_score: int | None = None
    created_at: datetime


class VerificationResultResponse(BaseModel):
    """Schema for verification result response."""

    qualification_id: int
    is_authentic: bool
    result: str
    method: str
    verification_hash: str | None = None
    ai_confidence_score: int | None = None
    message: str
    checks: dict | None = None
    ai_analysis: dict | None = None
    document_analysis: dict | None = None
    qualification: dict | None = None
    verified_at: datetime


class CredentialLookupResponse(BaseModel):
    """Schema for credential lookup by serial + registration number."""

    id: int
    title: str
    holder_name: str
    issuing_institution: str
    qualification_type: str
    grade: str | None = None
    status: str
    date_issued: datetime | None = None
    serial_number: str | None = None
    registration_number: str | None = None
    description: str | None = None
    credential_hash: str | None = None


class ExtractedCredentialData(BaseModel):
    """Schema for data extracted from an uploaded certificate/transcript."""

    holder_name: str | None = None
    issuing_institution: str | None = None
    title: str | None = None
    qualification_type: str | None = None
    grade: str | None = None
    serial_number: str | None = None
    registration_number: str | None = None
    date_issued: str | None = None
    holder_id_number: str | None = None
    raw_text: str | None = None
    confidence: dict | None = None
