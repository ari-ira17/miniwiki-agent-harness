"""FastAPI dependencies for current identity, CSRF and role checks."""

from collections.abc import Callable
from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.auth.sessions import (
    COOKIE_NAME,
    CSRF_COOKIE_NAME,
    find_session,
    verify_csrf,
)
from app.db import get_session
from app.models.auth_session import AuthSession
from app.models.user import User, UserRole
from app.services.permissions import PageScope, all_pages_scope, public_pages_scope

SessionDependency = Annotated[Session, Depends(get_session)]


def get_auth_session(
    request: Request, session: SessionDependency
) -> AuthSession | None:
    return find_session(session, request.cookies.get(COOKIE_NAME))


AuthSessionDependency = Annotated[AuthSession | None, Depends(get_auth_session)]


def require_csrf(request: Request, auth_session: AuthSessionDependency) -> None:
    if auth_session is None or not verify_csrf(
        auth_session,
        request.cookies.get(CSRF_COOKIE_NAME),
        request.headers.get("x-csrf-token"),
    ):
        raise HTTPException(status_code=403, detail="CSRF validation failed.")


CsrfDependency = Annotated[None, Depends(require_csrf)]


def require_user(auth_session: AuthSessionDependency) -> User:
    if auth_session is None or auth_session.user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Session"},
        )
    return auth_session.user


CurrentUser = Annotated[User, Depends(require_user)]


def require_html_user(auth_session: AuthSessionDependency) -> User:
    if auth_session is None or auth_session.user is None:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
        )
    return auth_session.user


def require_roles(*roles: UserRole) -> Callable[..., User]:
    def dependency(user: CurrentUser) -> User:
        if user.role not in roles:
            raise HTTPException(status_code=403, detail="Insufficient permissions.")
        return user

    return dependency


def page_scope_for(user: User) -> PageScope:
    return public_pages_scope if user.role is UserRole.READER else all_pages_scope


def get_html_page_scope(user: Annotated[User, Depends(require_html_user)]) -> PageScope:
    return page_scope_for(user)


def require_html_editor(user: Annotated[User, Depends(require_html_user)]) -> User:
    if user.role not in {UserRole.ADMIN, UserRole.EDITOR}:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    return user


def require_html_admin(user: Annotated[User, Depends(require_html_user)]) -> User:
    if user.role is not UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    return user
