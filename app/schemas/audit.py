"""Pydantic schemas for AuditLog model."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogResponse(BaseModel):
    """Schema for audit log response."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None = None
    qualification_id: int | None = None
    action: str
    entity_type: str
    entity_id: int | None = None
    description: str
    ip_address: str | None = None
    user_agent: str | None = None
    created_at: datetime


class AuditLogSearchResult(BaseModel):
    """Schema for paginated audit log search results."""

    items: list[AuditLogResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
