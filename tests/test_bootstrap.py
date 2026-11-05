"""Initial administrator bootstrap integration tests against PostgreSQL."""

from argon2 import PasswordHasher
from pydantic import SecretStr
from sqlalchemy import select
from sqlalchemy.orm import Session, sessionmaker

from app.bootstrap import (
    BootstrapConfigurationConflict,
    BootstrapResult,
    ensure_initial_admin,
)
from app.config import get_settings
from app.models.user import User, UserRole


def _configure_admin(monkeypatch, username: str, password: str) -> None:
    settings = get_settings().model_copy(
        update={"admin_username": username, "admin_password": SecretStr(password)}
    )
    monkeypatch.setattr("app.bootstrap.get_settings", lambda: settings)


def _users(sessions: sessionmaker[Session]) -> list[User]:
    with sessions() as session:
        return list(session.scalars(select(User).order_by(User.id)))


def test_creates_initial_admin_with_argon2_hash(user_sessions, monkeypatch) -> None:
    _configure_admin(monkeypatch, "first-admin", "temporary-test-password")

    result = ensure_initial_admin(user_sessions)

    users = _users(user_sessions)
    assert result is BootstrapResult.CREATED
    assert len(users) == 1
    assert users[0].username == "first-admin"
    assert users[0].first_name == get_settings().admin_first_name
    assert users[0].last_name == get_settings().admin_last_name
    assert users[0].full_name == f"{users[0].first_name} {users[0].last_name}"
    assert users[0].role is UserRole.ADMIN
    assert users[0].is_active is True
    assert users[0].password_hash != "temporary-test-password"
    assert PasswordHasher().verify(users[0].password_hash, "temporary-test-password")


def test_rerun_preserves_existing_admin_and_password(
    user_sessions, monkeypatch
) -> None:
    _configure_admin(monkeypatch, "first-admin", "temporary-test-password")
    ensure_initial_admin(user_sessions)
    original = _users(user_sessions)[0]
    original_hash = original.password_hash

    _configure_admin(monkeypatch, "changed-name", "different-test-password")
    result = ensure_initial_admin(user_sessions)

    users = _users(user_sessions)
    assert result is BootstrapResult.ALREADY_CONFIGURED
    assert len(users) == 1
    assert users[0].id == original.id
    assert users[0].username == "first-admin"
    assert users[0].password_hash == original_hash


def test_username_collision_does_not_promote_existing_user(
    user_sessions, monkeypatch
) -> None:
    _configure_admin(monkeypatch, "shared-name", "temporary-test-password")
    with user_sessions.begin() as session:
        session.add(
            User(
                username="shared-name",
                first_name="Existing",
                last_name="Editor",
                password_hash="$argon2id$existing",
                role=UserRole.EDITOR,
                is_active=True,
            )
        )

    try:
        ensure_initial_admin(user_sessions)
    except BootstrapConfigurationConflict as error:
        assert str(error) == (
            "Initial administrator configuration conflicts with an existing user."
        )
    else:
        raise AssertionError("Bootstrap must reject a conflicting username")

    users = _users(user_sessions)
    assert len(users) == 1
    assert users[0].role is UserRole.EDITOR


def test_inactive_admin_name_collision_is_not_reactivated(
    user_sessions, monkeypatch
) -> None:
    _configure_admin(monkeypatch, "inactive-admin", "temporary-test-password")
    with user_sessions.begin() as session:
        session.add(
            User(
                username="inactive-admin",
                first_name="Inactive",
                last_name="Admin",
                password_hash="$argon2id$existing",
                role=UserRole.ADMIN,
                is_active=False,
            )
        )

    try:
        ensure_initial_admin(user_sessions)
    except BootstrapConfigurationConflict:
        pass
    else:
        raise AssertionError("Bootstrap must reject the inactive admin collision")

    users = _users(user_sessions)
    assert len(users) == 1
    assert users[0].role is UserRole.ADMIN
    assert users[0].is_active is False


def test_case_insensitive_username_collision_blocks_bootstrap(
    user_sessions, monkeypatch
) -> None:
    _configure_admin(monkeypatch, "Alice", "temporary-test-password")
    with user_sessions.begin() as session:
        session.add(
            User(
                username="ALICE",
                first_name="Alice",
                last_name="Legacy",
                password_hash="$argon2id$existing",
                role=UserRole.EDITOR,
                is_active=True,
            )
        )

    try:
        ensure_initial_admin(user_sessions)
    except BootstrapConfigurationConflict:
        pass
    else:
        raise AssertionError("Bootstrap must reject a case-insensitive collision")

    users = _users(user_sessions)
    assert len(users) == 1
    assert users[0].username == "ALICE"
    assert users[0].role is UserRole.EDITOR
