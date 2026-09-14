"""Tests for the admin settings service (encrypted AI key storage)."""

import pytest
from cryptography.fernet import Fernet

from app.services.settings_service import (
    ANTHROPIC_API_KEY,
    OPENAI_API_KEY,
    SettingsService,
)


@pytest.fixture
def encryption_key(monkeypatch):
    """Configure a valid Fernet key on settings for the duration of the test."""
    key = Fernet.generate_key().decode()
    monkeypatch.setattr("app.services.settings_service.settings.ENCRYPTION_KEY", key)
    return key


@pytest.fixture
def no_env_keys(monkeypatch):
    """Clear env-var fallbacks so DB storage is the only source."""
    monkeypatch.setattr("app.services.settings_service.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.services.settings_service.settings.ANTHROPIC_API_KEY", "")


def test_is_encryption_configured_false_without_key(monkeypatch):
    monkeypatch.setattr("app.services.settings_service.settings.ENCRYPTION_KEY", "")
    assert SettingsService.is_encryption_configured() is False


def test_is_encryption_configured_true_with_key(encryption_key):
    assert SettingsService.is_encryption_configured() is True


def test_set_and_get_secret_roundtrip(db_session, encryption_key, no_env_keys):
    SettingsService.set_secret(db_session, OPENAI_API_KEY, "sk-test-123", "admin@test.com")
    assert SettingsService.get_secret(db_session, OPENAI_API_KEY) == "sk-test-123"


def test_stored_value_is_encrypted_not_plaintext(db_session, encryption_key, no_env_keys):
    SettingsService.set_secret(db_session, OPENAI_API_KEY, "sk-secret-999", "admin@test.com")
    from app.models import SystemSetting

    row = db_session.query(SystemSetting).filter(SystemSetting.id == OPENAI_API_KEY).first()
    assert row is not None
    assert "sk-secret-999" not in row.encrypted_value
    assert row.encrypted_value != "sk-secret-999"


def test_get_secret_falls_back_to_env_var(db_session, monkeypatch, encryption_key):
    monkeypatch.setattr("app.services.settings_service.settings.OPENAI_API_KEY", "sk-from-env")
    # Nothing stored in DB
    assert SettingsService.get_secret(db_session, OPENAI_API_KEY) == "sk-from-env"


def test_db_value_takes_precedence_over_env_var(db_session, encryption_key, monkeypatch):
    monkeypatch.setattr("app.services.settings_service.settings.OPENAI_API_KEY", "sk-from-env")
    SettingsService.set_secret(db_session, OPENAI_API_KEY, "sk-from-db", "admin@test.com")
    assert SettingsService.get_secret(db_session, OPENAI_API_KEY) == "sk-from-db"


def test_clear_secret_by_setting_empty(db_session, encryption_key, no_env_keys):
    SettingsService.set_secret(db_session, OPENAI_API_KEY, "sk-test", "admin@test.com")
    assert SettingsService.get_secret(db_session, OPENAI_API_KEY) == "sk-test"

    SettingsService.set_secret(db_session, OPENAI_API_KEY, "", "admin@test.com")
    from app.models import SystemSetting

    assert db_session.query(SystemSetting).filter(SystemSetting.id == OPENAI_API_KEY).first() is None
    assert SettingsService.get_secret(db_session, OPENAI_API_KEY) is None


def test_get_secret_returns_none_when_unset(db_session, encryption_key, no_env_keys):
    assert SettingsService.get_secret(db_session, OPENAI_API_KEY) is None


def test_list_settings_shows_unset_when_empty(db_session, encryption_key, no_env_keys):
    result = SettingsService.list_settings(db_session)
    assert len(result) == 2
    openai = next(r for r in result if r["key"] == OPENAI_API_KEY)
    assert openai["source"] == "unset"
    assert openai["masked_value"] == ""


def test_list_settings_shows_database_source(db_session, encryption_key, no_env_keys):
    SettingsService.set_secret(db_session, OPENAI_API_KEY, "sk-test-123456789", "admin@test.com")
    result = SettingsService.list_settings(db_session)
    openai = next(r for r in result if r["key"] == OPENAI_API_KEY)
    assert openai["source"] == "database"
    assert "stored" in openai["masked_value"]


def test_list_settings_shows_environment_source(db_session, encryption_key, monkeypatch):
    monkeypatch.setattr("app.services.settings_service.settings.OPENAI_API_KEY", "sk-env-123456789")
    result = SettingsService.list_settings(db_session)
    openai = next(r for r in result if r["key"] == OPENAI_API_KEY)
    assert openai["source"] == "environment"
    assert "sk-e" in openai["masked_value"]  # first 4 chars
    assert "6789" in openai["masked_value"]  # last 4 chars


def test_list_settings_never_returns_plaintext(db_session, encryption_key, no_env_keys):
    SettingsService.set_secret(db_session, OPENAI_API_KEY, "sk-supersecret-key-123", "admin@test.com")
    result = SettingsService.list_settings(db_session)
    openai = next(r for r in result if r["key"] == OPENAI_API_KEY)
    assert "sk-supersecret-key-123" not in openai["masked_value"]


def test_set_secret_without_encryption_key_raises(db_session, monkeypatch, no_env_keys):
    monkeypatch.setattr("app.services.settings_service.settings.ENCRYPTION_KEY", "")
    with pytest.raises(RuntimeError):
        SettingsService.set_secret(db_session, OPENAI_API_KEY, "sk-test", "admin@test.com")


def test_anthropic_key_roundtrip(db_session, encryption_key, no_env_keys):
    SettingsService.set_secret(db_session, ANTHROPIC_API_KEY, "ant-key-123", "admin@test.com")
    assert SettingsService.get_secret(db_session, ANTHROPIC_API_KEY) == "ant-key-123"
