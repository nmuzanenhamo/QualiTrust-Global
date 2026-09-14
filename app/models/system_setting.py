"""System settings model for storing encrypted configuration values.

API keys and other secrets entered through the admin settings UI are stored
here in encrypted form (Fernet). The plaintext never touches the database.
"""

from datetime import datetime

from sqlalchemy import Column, DateTime, String, Text

from app.core.database import Base


class SystemSetting(Base):
    """Key/value store for application configuration.

    Values are encrypted at rest using Fernet (see SettingsService). The
    `key` column holds a stable identifier such as ``openai_api_key``.
    """

    __tablename__ = "system_settings"

    id = Column(String(100), primary_key=True)
    encrypted_value = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(String(255), nullable=True)
