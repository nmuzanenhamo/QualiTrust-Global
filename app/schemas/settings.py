"""Pydantic schemas for the admin settings API."""

from datetime import datetime

from pydantic import BaseModel, Field


class SettingItem(BaseModel):
    """A single managed setting as returned to the admin UI."""

    key: str
    label: str
    description: str
    env_var: str
    source: str = Field(description="database | environment | unset")
    masked_value: str
    updated_at: datetime | None = None


class SettingsResponse(BaseModel):
    """All managed settings plus encryption status."""

    encryption_configured: bool
    settings: list[SettingItem]


class UpdateSettingRequest(BaseModel):
    """Request body for updating a single secret."""

    value: str = Field(
        description="The plaintext secret. Send an empty string to clear the stored value.",
    )
