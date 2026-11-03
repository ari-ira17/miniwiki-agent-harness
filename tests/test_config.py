"""Configuration validation tests."""

import pytest
from pydantic import SecretStr, ValidationError

from app.config import Settings


def test_settings_load_required_values_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("POSTGRES_USER", "wiki")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss:word")
    monkeypatch.setenv("POSTGRES_DB", "wiki")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "initial-secret-123")

    settings = Settings(_env_file=None)

    assert settings.database_url == (
        "postgresql+psycopg://wiki:p%40ss%3Aword@db:5432/wiki?connect_timeout=3"
    )
    assert settings.admin_username == "admin"
    assert settings.admin_password == SecretStr("initial-secret-123")
    assert "initial-secret-123" not in repr(settings)


def test_settings_reject_missing_required_values(monkeypatch) -> None:
    for key in (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "ADMIN_USERNAME",
        "ADMIN_PASSWORD",
    ):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
