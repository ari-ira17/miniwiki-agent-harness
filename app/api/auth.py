"""Login, logout, current identity and CSRF token API."""

import hmac
import secrets
from typing import Annotated as TypingAnnotated

from fastapi import APIRouter, HTTPException, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field, SecretStr, StringConstraints

from app.auth.dependencies import (
    AuthSessionDependency,
    CsrfDependency,
    SessionDependency,
)
from app.auth.sessions import (
    COOKIE_NAME,
    CSRF_COOKIE_NAME,
    create_session,
    digest,
    dummy_password_check,
    verify_password,
)
from app.auth.usernames import find_user_by_username
from app.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["authentication"])
Username = TypingAnnotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=64)
]


class LoginRequest(BaseModel):
    model_config = ConfigDict(hide_input_in_errors=True, extra="forbid")

    username: Username
    password: SecretStr = Field(min_length=1, max_length=256)


class Identity(BaseModel):
    id: int
    username: str
    role: str
    first_name: str
    last_name: str
    full_name: str


def _set_cookies(response: Response, token: str, csrf: str) -> None:
    settings = get_settings()
    common = {
        "max_age": 8 * 60 * 60,
        "secure": settings.session_cookie_secure,
        "samesite": "lax",
        "path": "/",
    }
    response.set_cookie(COOKIE_NAME, token, httponly=True, **common)
    response.set_cookie(CSRF_COOKIE_NAME, csrf, httponly=False, **common)


def _clear_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=True,
        samesite="lax",
    )
    response.delete_cookie(
        CSRF_COOKIE_NAME,
        path="/",
        secure=settings.session_cookie_secure,
        httponly=False,
        samesite="lax",
    )


@router.get("/csrf", summary="Get a CSRF token")
def get_csrf_token(
    request: Request,
    response: Response,
    session: SessionDependency,
    auth_session: AuthSessionDependency,
) -> dict[str, str]:
    """Create an anonymous session or return its double-submit CSRF token."""
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME)
    record = auth_session
    if record is None:
        token, csrf, _ = create_session(session, None)
        session.commit()
    elif cookie_token:
        if hmac.compare_digest(record.csrf_hash, digest(cookie_token)):
            return {"csrf_token": cookie_token}
        csrf = secrets.token_urlsafe(32)
        record.csrf_hash = digest(csrf)
        session.commit()
        token = request.cookies[COOKIE_NAME]
    else:
        csrf = secrets.token_urlsafe(32)
        record.csrf_hash = digest(csrf)
        session.commit()
        token = request.cookies[COOKIE_NAME]
    _set_cookies(response, token, csrf)
    return {"csrf_token": csrf}


@router.post("/login", response_model=Identity, summary="Sign in")
def login(
    data: LoginRequest,
    response: Response,
    session: SessionDependency,
    _csrf: CsrfDependency,
    auth_session: AuthSessionDependency,
) -> Identity:
    """Verify Argon2 credentials and rotate the anonymous session token."""
    password = data.password.get_secret_value()
    user = find_user_by_username(session, data.username)
    if user is None:
        dummy_password_check(password)
        password_valid = False
    else:
        password_valid = verify_password(user.password_hash, password)
    if user is None or not user.is_active or not password_valid:
        raise HTTPException(status_code=401, detail="Invalid username or password.")

    if auth_session is not None:
        session.delete(auth_session)
    token, csrf, _ = create_session(session, user)
    session.commit()
    _set_cookies(response, token, csrf)
    return Identity(
        id=user.id,
        username=user.username,
        role=user.role.value,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Sign out")
def logout(
    session: SessionDependency,
    _csrf: CsrfDependency,
    auth_session: AuthSessionDependency,
) -> Response:
    if auth_session is not None:
        session.delete(auth_session)
        session.commit()
    response = Response(status_code=status.HTTP_204_NO_CONTENT)
    _clear_cookies(response)
    return response


@router.get("/me", response_model=Identity, summary="Current identity")
def who_am_i(auth_session: AuthSessionDependency) -> Identity:
    if auth_session is None or auth_session.user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    user = auth_session.user
    return Identity(
        id=user.id,
        username=user.username,
        role=user.role.value,
        first_name=user.first_name,
        last_name=user.last_name,
        full_name=user.full_name,
    )
