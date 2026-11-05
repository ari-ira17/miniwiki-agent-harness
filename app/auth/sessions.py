"""Session token, password verification and CSRF primitives."""

import hashlib
import hmac
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.auth_session import AuthSession
from app.models.user import User

SESSION_TTL = timedelta(hours=8)
COOKIE_NAME = "miniwiki_session"
CSRF_COOKIE_NAME = "miniwiki_csrf"
_password_hasher = PasswordHasher()
_dummy_hash = _password_hasher.hash("dummy-password-never-used")
_TOKEN_LENGTH = 43
_TOKEN_ALPHABET = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-"
)


def _is_token(value: str | None) -> bool:
    return bool(
        value
        and len(value) == _TOKEN_LENGTH
        and value.isascii()
        and all(character in _TOKEN_ALPHABET for character in value)
    )


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def create_session(session: Session, user: User | None) -> tuple[str, str, AuthSession]:
    token = secrets.token_urlsafe(32)
    csrf = secrets.token_urlsafe(32)
    record = AuthSession(
        token_hash=digest(token),
        csrf_hash=digest(csrf),
        user_id=user.id if user else None,
        expires_at=datetime.now(UTC) + SESSION_TTL,
    )
    session.add(record)
    session.flush()
    return token, csrf, record


def find_session(session: Session, token: str | None) -> AuthSession | None:
    if not _is_token(token):
        return None
    record = session.scalar(
        select(AuthSession).where(AuthSession.token_hash == digest(token))
    )
    if record is None or record.expires_at <= datetime.now(UTC):
        if record is not None:
            session.delete(record)
            session.commit()
        return None
    if record.user_id is not None and (
        record.user is None or not record.user.is_active
    ):
        session.delete(record)
        session.commit()
        return None
    return record


def revoke_user_sessions(session: Session, user_id: int) -> None:
    session.execute(delete(AuthSession).where(AuthSession.user_id == user_id))


def verify_csrf(record: AuthSession, cookie: str | None, header: str | None) -> bool:
    if not _is_token(cookie) or not _is_token(header):
        return False
    if not hmac.compare_digest(cookie.encode("ascii"), header.encode("ascii")):
        return False
    return hmac.compare_digest(record.csrf_hash, digest(header))


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (VerifyMismatchError, VerificationError, InvalidHashError):
        return False


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def dummy_password_check(password: str) -> None:
    """Spend a password verification for unknown usernames too."""
    verify_password(_dummy_hash, password)
