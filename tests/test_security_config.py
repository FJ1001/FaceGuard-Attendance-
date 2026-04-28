"""Security configuration validation tests."""

import pytest

import config.settings as settings


def _set_required_config(monkeypatch):
    monkeypatch.setattr(settings, "SECRET_KEY", "x" * 40)
    monkeypatch.setattr(settings, "SALT", "salt-value-with-16-plus-chars")
    monkeypatch.setattr(settings, "ADMIN_EMAIL", "admin@example.com")
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "strong-admin-password")
    monkeypatch.setattr(settings, "MIN_PASSWORD_LENGTH", 8)
    monkeypatch.setattr(settings, "BIOMETRIC_CACHE_ENABLED", False)
    monkeypatch.setattr(settings, "BIOMETRIC_CACHE_ENCRYPTION_KEY", None)


def test_validate_security_config_accepts_strong_required_values(monkeypatch):
    _set_required_config(monkeypatch)

    settings.validate_security_config()


def test_validate_security_config_rejects_missing_secret(monkeypatch):
    _set_required_config(monkeypatch)
    monkeypatch.setattr(settings, "SECRET_KEY", None)

    with pytest.raises(settings.ConfigurationError, match="SECRET_KEY"):
        settings.validate_security_config()


def test_validate_security_config_rejects_default_admin_password(monkeypatch):
    _set_required_config(monkeypatch)
    monkeypatch.setattr(settings, "ADMIN_PASSWORD", "admin123")

    with pytest.raises(settings.ConfigurationError, match="ADMIN_PASSWORD"):
        settings.validate_security_config()


def test_biometric_cache_requires_encryption_key(monkeypatch):
    _set_required_config(monkeypatch)
    monkeypatch.setattr(settings, "BIOMETRIC_CACHE_ENABLED", True)
    monkeypatch.setattr(settings, "BIOMETRIC_CACHE_ENCRYPTION_KEY", None)

    with pytest.raises(settings.ConfigurationError, match="BIOMETRIC_CACHE_ENCRYPTION_KEY"):
        settings.validate_security_config()
