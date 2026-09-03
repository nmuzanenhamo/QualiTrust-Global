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
    verified_at: datetime
