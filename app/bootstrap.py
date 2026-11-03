"""Safe, repeatable creation of the initial administrator."""

import sys
from enum import StrEnum

from argon2 import PasswordHasher
from sqlalchemy import select, text
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings
from app.db import get_session_factory
from app.models.user import User, UserRole

_BOOTSTRAP_LOCK_ID = 783_242_051_007
_password_hasher = PasswordHasher()


class BootstrapResult(StrEnum):
    CREATED = "created"
    ALREADY_CONFIGURED = "already_configured"


class BootstrapConfigurationConflict(RuntimeError):
    """Raised when the configured admin name belongs to an unsafe account."""

    def __init__(self) -> None:
        super().__init__(
            "Initial administrator configuration conflicts with an existing user."
        )


def ensure_initial_admin(
    session_factory: sessionmaker[Session],
) -> BootstrapResult:
    """Ensure one active admin exists without changing any existing account."""
    settings = get_settings()
    with session_factory() as session, session.begin():
        # Serialize competing app startups to prevent duplicate bootstrap admins.
        session.execute(
            text("SELECT pg_advisory_xact_lock(:lock_id)"),
            {"lock_id": _BOOTSTRAP_LOCK_ID},
        )

        active_admin = session.scalar(
            select(User.id)
            .where(User.role == UserRole.ADMIN, User.is_active.is_(True))
            .limit(1)
        )
        if active_admin is not None:
            return BootstrapResult.ALREADY_CONFIGURED

        conflicting_user = session.scalar(
            select(User.id).where(User.username == settings.admin_username).limit(1)
        )
        if conflicting_user is not None:
            raise BootstrapConfigurationConflict() from None

        session.add(
            User(
                username=settings.admin_username,
                password_hash=_password_hasher.hash(
                    settings.admin_password.get_secret_value()
                ),
                role=UserRole.ADMIN,
                is_active=True,
            )
        )
    return BootstrapResult.CREATED


def main() -> None:
    result = ensure_initial_admin(get_session_factory())
    print(f"Initial admin bootstrap: {result.value}")


if __name__ == "__main__":
    try:
        main()
    except BootstrapConfigurationConflict as error:
        print(str(error), file=sys.stderr)
        raise SystemExit(1) from None
