"""Pydantic schemas for Qualification model."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class QualificationBase(BaseModel):
    """Base qualification schema."""

    title: str
    qualification_type: str
    issuing_institution: str
    holder_name: str
    holder_email: str | None = None
    holder_id_number: str | None = None
    date_issued: datetime
    date_expires: datetime | None = None
    registration_number: str | None = None
    serial_number: str | None = None
    description: str | None = None


class QualificationCreate(QualificationBase):
    """Schema for creating a qualification."""
    pass


class QualificationUpdate(BaseModel):
    """Schema for updating a qualification."""

    title: str | None = None
    qualification_type: str | None = None
    issuing_institution: str | None = None
    holder_name: str | None = None
    holder_email: str | None = None
    holder_id_number: str | None = None
    date_issued: datetime | None = None
    date_expires: datetime | None = None
    registration_number: str | None = None
    serial_number: str | None = None
    description: str | None = None
    status: str | None = None


class QualificationResponse(QualificationBase):
    """Schema for qualification response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    status: str
    credential_hash: str | None = None
    registered_by: int
    created_at: datetime
    updated_at: datetime


class QualificationSearchResult(BaseModel):
    """Schema for paginated search results."""

    items: list[QualificationResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
