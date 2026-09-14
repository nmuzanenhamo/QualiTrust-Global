"""Integration tests for the admin settings router."""

import pytest
from cryptography.fernet import Fernet

from app.services.settings_service import OPENAI_API_KEY


@pytest.fixture
def encryption_key(monkeypatch):
    key = Fernet.generate_key().decode()
    monkeypatch.setattr("app.services.settings_service.settings.ENCRYPTION_KEY", key)
    monkeypatch.setattr("app.core.config.settings.ENCRYPTION_KEY", key)
    return key


@pytest.fixture
def clean_env(monkeypatch):
    monkeypatch.setattr("app.services.settings_service.settings.OPENAI_API_KEY", "")
    monkeypatch.setattr("app.services.settings_service.settings.ANTHROPIC_API_KEY", "")


def test_get_settings_requires_auth(client):
    response = client.get("/api/v1/settings")
    assert response.status_code == 401


def test_get_settings_requires_admin(client, viewer_headers):
    response = client.get("/api/v1/settings", headers=viewer_headers)
    assert response.status_code == 403


def test_admin_can_get_settings(client, admin_headers, encryption_key, clean_env):
    response = client.get("/api/v1/settings", headers=admin_headers)
    assert response.status_code == 200
    body = response.json()
    assert body["encryption_configured"] is True
    keys = [s["key"] for s in body["settings"]]
    assert "openai_api_key" in keys
    assert "anthropic_api_key" in keys


def test_update_setting_requires_admin(client, viewer_headers, encryption_key, clean_env):
    response = client.put(
        "/api/v1/settings/openai_api_key",
        json={"value": "sk-test"},
        headers=viewer_headers,
    )
    assert response.status_code == 403


def test_admin_can_update_setting(client, admin_headers, db_session, encryption_key, clean_env):
    response = client.put(
        "/api/v1/settings/openai_api_key",
        json={"value": "sk-test-12345"},
        headers=admin_headers,
    )
    assert response.status_code == 200
    assert response.json()["status"] == "updated"

    from app.services.settings_service import SettingsService

    assert SettingsService.get_secret(db_session, OPENAI_API_KEY) == "sk-test-12345"


def test_update_unknown_key_returns_404(client, admin_headers, encryption_key, clean_env):
    response = client.put(
        "/api/v1/settings/nonexistent_key",
        json={"value": "x"},
        headers=admin_headers,
    )
    assert response.status_code == 404


def test_clear_setting_with_empty_value(client, admin_headers, db_session, encryption_key, clean_env):
    # Set first
    client.put(
        "/api/v1/settings/openai_api_key",
        json={"value": "sk-test"},
        headers=admin_headers,
    )
    # Then clear
    response = client.put(
        "/api/v1/settings/openai_api_key",
        json={"value": ""},
        headers=admin_headers,
    )
    assert response.status_code == 200

    from app.models import SystemSetting

    assert db_session.query(SystemSetting).filter(SystemSetting.id == OPENAI_API_KEY).first() is None


def test_get_settings_masks_values(client, admin_headers, encryption_key, clean_env):
    client.put(
        "/api/v1/settings/openai_api_key",
        json={"value": "sk-supersecret-12345678"},
        headers=admin_headers,
    )
    response = client.get("/api/v1/settings", headers=admin_headers)
    body = response.json()
    openai = next(s for s in body["settings"] if s["key"] == "openai_api_key")
    assert "sk-supersecret-12345678" not in openai["masked_value"]


def test_update_without_encryption_key_returns_400(client, admin_headers, monkeypatch, clean_env):
    monkeypatch.setattr("app.services.settings_service.settings.ENCRYPTION_KEY", "")
    response = client.put(
        "/api/v1/settings/openai_api_key",
        json={"value": "sk-test"},
        headers=admin_headers,
    )
    assert response.status_code == 400
