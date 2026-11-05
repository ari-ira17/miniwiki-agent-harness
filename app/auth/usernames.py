"""Shared username normalization and collision lookup."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.user import User


def canonicalize_username(username: str) -> str:
    """Return the case-insensitive canonical form used for new identities."""
    return username.strip().casefold()


def find_user_by_username(session: Session, username: str) -> User | None:
    """Find one case-insensitive identity, locking its row before login checks."""
    canonical = canonicalize_username(username)
    candidates = session.execute(select(User.id, User.username)).all()
    matches = [
        (user_id, stored_name)
        for user_id, stored_name in candidates
        if canonicalize_username(stored_name) == canonical
    ]
    if not matches:
        return None
    if len(matches) > 1:
        exact_matches = [match for match in matches if match[1] == username]
        if len(exact_matches) != 1:
            return None
        user_id = exact_matches[0][0]
    else:
        user_id = matches[0][0]
    return session.scalar(
        select(User)
        .where(User.id == user_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )


def username_exists(session: Session, username: str) -> bool:
    """Compare existing stored names using the shared Unicode casefold rule."""
    canonical = canonicalize_username(username)
    return any(
        canonicalize_username(stored_name) == canonical
        for stored_name in session.scalars(select(User.username))
    )
