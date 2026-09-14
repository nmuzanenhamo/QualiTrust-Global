"""Admin-only router for managing AI integration keys via the UI.

Keys are encrypted at rest (Fernet) and never returned in plaintext.
GET returns masked values + source (database/environment/unset).
PUT stores a new value (empty string clears it).
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_admin
from app.models import User
from app.schemas.settings import SettingsResponse, UpdateSettingRequest
from app.services.settings_service import MANAGED_KEYS, SettingsService

router = APIRouter()

_VALID_KEYS = {m["key"] for m in MANAGED_KEYS}


@router.get("", response_model=SettingsResponse)
def get_settings(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """List all managed AI integration keys (masked)."""
    return SettingsResponse(
        encryption_configured=SettingsService.is_encryption_configured(),
        settings=SettingsService.list_settings(db),
    )


@router.put("/{key}", status_code=status.HTTP_200_OK)
def update_setting(
    key: str,
    body: UpdateSettingRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """Create, update, or clear a managed secret."""
    if key not in _VALID_KEYS:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown setting key: {key}",
        )

    if body.value and not SettingsService.is_encryption_configured():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "ENCRYPTION_KEY is not configured on the server. Set it as an "
                "environment variable before storing secrets in the database."
            ),
        )

    SettingsService.set_secret(db, key, body.value, updated_by=current_user.email)
    return {"status": "updated", "key": key}
