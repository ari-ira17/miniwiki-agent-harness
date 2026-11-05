"""Admin-only user account operations with serialized admin protection."""

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.auth.sessions import hash_password, revoke_user_sessions
from app.auth.usernames import username_exists
from app.bootstrap import BOOTSTRAP_ADMIN_LOCK_ID
from app.models.user import User, UserRole
from app.schemas.users import UserCreate, UserUpdate


class UserNotFound(Exception):
    """Raised when an account does not exist."""


class UsernameConflict(Exception):
    """Raised when a username is already taken."""


class LastActiveAdmin(Exception):
    """Raised when an operation would remove the final active administrator."""


class ActorNoLongerAdmin(Exception):
    """Raised when an administrator lost authority before a mutation acquired its lock."""


def _lock_and_authorize(session: Session, actor_id: int) -> User:
    session.execute(
        text("SELECT pg_advisory_xact_lock(:lock_id)"),
        {"lock_id": BOOTSTRAP_ADMIN_LOCK_ID},
    )
    actor = session.scalar(
        select(User)
        .where(User.id == actor_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if actor is None or not actor.is_active or actor.role is not UserRole.ADMIN:
        raise ActorNoLongerAdmin
    return actor


def list_users(session: Session) -> list[User]:
    return list(session.scalars(select(User).order_by(User.username)))


def create_user(session: Session, actor_id: int, data: UserCreate) -> User:
    _lock_and_authorize(session, actor_id)
    if username_exists(session, data.username):
        session.rollback()
        raise UsernameConflict
    user = User(
        username=data.username,
        first_name=data.first_name,
        last_name=data.last_name,
        password_hash=hash_password(data.password.get_secret_value()),
        role=data.role,
        is_active=True,
    )
    session.add(user)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        raise UsernameConflict from error
    session.refresh(user)
    return user


def update_user(
    session: Session, actor_id: int, user_id: int, data: UserUpdate
) -> User:
    _lock_and_authorize(session, actor_id)
    target = session.scalar(select(User).where(User.id == user_id).with_for_update())
    if target is None:
        session.rollback()
        raise UserNotFound

    changes = data.model_dump(exclude_unset=True)
    demotes_or_disables = (
        target.is_active
        and target.role is UserRole.ADMIN
        and (
            changes.get("role", target.role) is not UserRole.ADMIN
            or changes.get("is_active", target.is_active) is False
        )
    )
    if demotes_or_disables:
        active_admins = session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.ADMIN, User.is_active.is_(True))
        )
        if active_admins <= 1:
            session.rollback()
            raise LastActiveAdmin

    password = changes.pop("password", None)
    role = changes.pop("role", None)
    is_active = changes.pop("is_active", None)
    first_name = changes.pop("first_name", None)
    last_name = changes.pop("last_name", None)
    if first_name is not None:
        target.first_name = first_name
    if last_name is not None:
        target.last_name = last_name
    identity_changed = False
    if role is not None and target.role is not role:
        target.role = role
        identity_changed = True
    if is_active is not None and target.is_active != is_active:
        target.is_active = is_active
        if not is_active:
            identity_changed = True
    if password is not None:
        target.password_hash = hash_password(password.get_secret_value())
        identity_changed = True
    if identity_changed:
        revoke_user_sessions(session, target.id)
    session.commit()
    session.refresh(target)
    return target


def delete_user(session: Session, actor_id: int, user_id: int) -> None:
    _lock_and_authorize(session, actor_id)
    target = session.scalar(select(User).where(User.id == user_id).with_for_update())
    if target is None:
        session.rollback()
        raise UserNotFound
    if target.is_active and target.role is UserRole.ADMIN:
        active_admins = session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.ADMIN, User.is_active.is_(True))
        )
        if active_admins <= 1:
            session.rollback()
            raise LastActiveAdmin
    revoke_user_sessions(session, target.id)
    session.delete(target)
    session.commit()
