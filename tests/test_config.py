"""Configuration validation tests."""

import pytest
from pydantic import SecretStr, ValidationError

from app.config import Settings


@pytest.mark.parametrize(
    ("host", "port"),
    [(None, None), ("localhost", "55432")],
    ids=["defaults", "explicit-host-and-port"],
)
def test_settings_load_required_values_from_environment(
    monkeypatch, host: str | None, port: str | None
) -> None:
    monkeypatch.setenv("POSTGRES_USER", "wiki")
    monkeypatch.setenv("POSTGRES_PASSWORD", "p@ss:word")
    monkeypatch.setenv("POSTGRES_DB", "wiki")
    monkeypatch.setenv("ADMIN_USERNAME", "admin")
    monkeypatch.setenv("ADMIN_PASSWORD", "initial-secret-123")
    monkeypatch.setenv("ADMIN_FIRST_NAME", "Test")
    monkeypatch.setenv("ADMIN_LAST_NAME", "Administrator")

    for key, value in (("POSTGRES_HOST", host), ("POSTGRES_PORT", port)):
        if value is None:
            monkeypatch.delenv(key, raising=False)
        else:
            monkeypatch.setenv(key, value)

    settings = Settings(_env_file=None)

    assert settings.database_url == (
        f"postgresql+psycopg://wiki:p%40ss%3Aword@{host or 'db'}:"
        f"{port or '5432'}/wiki?connect_timeout=3"
    )
    assert settings.admin_username == "admin"
    assert settings.admin_password == SecretStr("initial-secret-123")
    assert settings.admin_first_name == "Test"
    assert settings.admin_last_name == "Administrator"
    assert "initial-secret-123" not in repr(settings)


def test_settings_reject_missing_required_values(monkeypatch) -> None:
    for key in (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "ADMIN_USERNAME",
        "ADMIN_PASSWORD",
        "ADMIN_FIRST_NAME",
        "ADMIN_LAST_NAME",
    ):
        monkeypatch.delenv(key, raising=False)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)


def test_settings_reject_control_characters_in_admin_profile(monkeypatch) -> None:
    for key, value in {
        "POSTGRES_USER": "wiki",
        "POSTGRES_PASSWORD": "secret",
        "POSTGRES_DB": "wiki",
        "ADMIN_USERNAME": "admin",
        "ADMIN_PASSWORD": "initial-secret-123",
        "ADMIN_FIRST_NAME": "Admin\nName",
        "ADMIN_LAST_NAME": "User",
    }.items():
        monkeypatch.setenv(key, value)

    with pytest.raises(ValidationError):
        Settings(_env_file=None)
