"""Service for reading and writing encrypted application settings.

API keys entered through the admin settings UI are encrypted with Fernet
before being written to the ``system_settings`` table. Plaintext values are
only ever held in memory while a request is being served.

Resolution order for a secret (e.g. the OpenAI key):
1. Database (encrypted) — set via the admin Settings page.
2. Environment variable — set at deploy time (e.g. ``flyctl secrets set``).

This lets operators choose whichever workflow they prefer.
"""

import logging

from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import SystemSetting

logger = logging.getLogger(__name__)

# Stable keys stored in the system_settings table.
OPENAI_API_KEY = "openai_api_key"
ANTHROPIC_API_KEY = "anthropic_api_key"

# Settings exposed to the admin UI. Order matters for display.
MANAGED_KEYS = [
    {
        "key": OPENAI_API_KEY,
        "label": "OpenAI API Key",
        "description": "Used for GPT-4o-mini vision extraction and AI fraud analysis.",
        "env_var": "OPENAI_API_KEY",
    },
    {
        "key": ANTHROPIC_API_KEY,
        "label": "Anthropic API Key",
        "description": "Reserved for future Claude-based analysis. Not yet wired in.",
        "env_var": "ANTHROPIC_API_KEY",
    },
]


class SettingsService:
    """Encrypted key/value store for admin-managed secrets."""

    @staticmethod
    def _fernet() -> Fernet | None:
        """Build a Fernet instance from the configured ENCRYPTION_KEY.

        Returns None if no key is configured, so callers can gracefully
        skip DB-backed settings and fall back to environment variables.
        """
        key = settings.ENCRYPTION_KEY
        if not key:
            return None
        try:
            return Fernet(key.encode() if isinstance(key, str) else key)
        except (ValueError, TypeError) as exc:
            logger.warning(f"ENCRYPTION_KEY is set but invalid: {exc}")
            return None

    @staticmethod
    def _encrypt(plaintext: str) -> str:
        f = SettingsService._fernet()
        if f is None:
            raise RuntimeError(
                "ENCRYPTION_KEY is not configured. Set it as an environment "
                "variable before storing secrets in the database."
            )
        return f.encrypt(plaintext.encode()).decode()

    @staticmethod
    def _decrypt(ciphertext: str) -> str:
        f = SettingsService._fernet()
        if f is None:
            raise RuntimeError("ENCRYPTION_KEY is not configured; cannot decrypt.")
        return f.decrypt(ciphertext.encode()).decode()

    @staticmethod
    def get_secret(db: Session, key: str) -> str | None:
        """Return the plaintext secret for ``key``, or None if not stored.

        Resolution order:
        1. Database (decrypted)
        2. Environment variable (matching the managed key's env_var)
        """
        row = db.query(SystemSetting).filter(SystemSetting.id == key).first()
        if row and row.encrypted_value:
            try:
                return SettingsService._decrypt(row.encrypted_value)
            except InvalidToken:
                logger.warning(f"Stored value for {key} could not be decrypted (key rotated?)")

        # Fall back to environment variable.
        env_var = next((m["env_var"] for m in MANAGED_KEYS if m["key"] == key), None)
        if env_var:
            return getattr(settings, env_var, None) or None
        return None

    @staticmethod
    def set_secret(db: Session, key: str, value: str, updated_by: str | None = None) -> None:
        """Encrypt and persist a secret. Empty string clears the stored value."""
        if value == "":
            # Clear the stored value so the env var (if any) takes over again.
            row = db.query(SystemSetting).filter(SystemSetting.id == key).first()
            if row:
                db.delete(row)
                db.commit()
            return

        encrypted = SettingsService._encrypt(value)
        row = db.query(SystemSetting).filter(SystemSetting.id == key).first()
        if row:
            row.encrypted_value = encrypted
            row.updated_by = updated_by
        else:
            row = SystemSetting(id=key, encrypted_value=encrypted, updated_by=updated_by)
            db.add(row)
        db.commit()

    @staticmethod
    def list_settings(db: Session) -> list[dict]:
        """Return all managed keys with masked values and source labels.

        Never returns plaintext. Used by the admin Settings page.
        """
        rows = {r.id: r for r in db.query(SystemSetting).all()}
        result = []
        for meta in MANAGED_KEYS:
            key = meta["key"]
            row = rows.get(key)
            env_value = getattr(settings, meta["env_var"], "") or ""
            if row and row.encrypted_value:
                source = "database"
                masked = "•••••••• (stored)"
            elif env_value:
                source = "environment"
                masked = SettingsService._mask(env_value)
            else:
                source = "unset"
                masked = ""
            result.append(
                {
                    "key": key,
                    "label": meta["label"],
                    "description": meta["description"],
                    "env_var": meta["env_var"],
                    "source": source,
                    "masked_value": masked,
                    "updated_at": row.updated_at if row else None,
                }
            )
        return result

    @staticmethod
    def _mask(value: str) -> str:
        if not value:
            return ""
        if len(value) <= 8:
            return "••••"
        return value[:4] + "••••" + value[-4:]

    @staticmethod
    def is_encryption_configured() -> bool:
        """True if ENCRYPTION_KEY is set and valid."""
        return SettingsService._fernet() is not None
