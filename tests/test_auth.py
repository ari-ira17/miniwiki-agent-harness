"""Authentication and server-side session lifecycle checks."""

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import select

from app.auth.sessions import COOKIE_NAME, CSRF_COOKIE_NAME, digest
from app.models.auth_session import AuthSession
from app.models.user import User
from tests.conftest import login_as


def test_login_rotates_anonymous_token_and_stores_only_hash(auth_client, page_sessions):
    csrf = auth_client.get("/api/auth/csrf")
    assert csrf.status_code == 200
    anonymous_token = auth_client.cookies[COOKIE_NAME]
    anonymous_csrf = csrf.json()["csrf_token"]
    assert csrf.headers["cache-control"] == "no-store"
    assert auth_client.cookies.get(COOKIE_NAME) == anonymous_token
    assert auth_client.cookies.get(CSRF_COOKIE_NAME) == anonymous_csrf

    response = auth_client.post(
        "/api/auth/login",
        json={"username": "test-reader", "password": "test-password-123"},
        headers={"X-CSRF-Token": anonymous_csrf},
    )
    assert response.status_code == 200
    assert response.json()["role"] == "reader"
    assert response.headers["referrer-policy"] == "same-origin"
    assert auth_client.cookies[COOKIE_NAME] != anonymous_token
    assert response.cookies[COOKIE_NAME] != anonymous_token
    assert response.headers.get_list("set-cookie")[0].lower().find("httponly") >= 0

    with page_sessions() as session:
        records = list(session.scalars(select(AuthSession)))
        assert len(records) == 1
        assert records[0].token_hash == digest(auth_client.cookies[COOKIE_NAME])
        assert records[0].token_hash != auth_client.cookies[COOKIE_NAME]
        assert records[0].expires_at > datetime.now(UTC) + timedelta(hours=7)
    assert auth_client.get("/api/auth/me").json()["username"] == "test-reader"


def test_logout_revokes_session_and_clears_cookies(auth_client):
    login_as(auth_client, "test-admin")
    csrf = auth_client.get("/api/auth/csrf").json()["csrf_token"]
    response = auth_client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf})
    assert response.status_code == 204
    assert COOKIE_NAME in response.headers["set-cookie"]
    assert auth_client.get("/api/auth/me").status_code == 401


def test_expired_session_is_rejected_and_removed(auth_client, page_sessions):
    login_as(auth_client, "test-admin")
    with page_sessions.begin() as session:
        record = session.scalar(select(AuthSession))
        assert record is not None
        record.expires_at = datetime.now(UTC) - timedelta(seconds=1)
    assert auth_client.get("/api/auth/me").status_code == 401
    with page_sessions() as session:
        assert session.scalar(select(AuthSession.id)) is None


def test_tampered_and_logged_out_session_tokens_are_rejected(auth_client):
    login_as(auth_client, "test-admin")
    old_token = auth_client.cookies[COOKIE_NAME]
    csrf = auth_client.get("/api/auth/csrf").json()["csrf_token"]
    assert (
        auth_client.post("/api/auth/logout", headers={"X-CSRF-Token": csrf}).status_code
        == 204
    )
    auth_client.cookies.set(COOKIE_NAME, old_token)
    assert auth_client.get("/api/auth/me").status_code == 401
    auth_client.cookies.set(COOKIE_NAME, "tampered-token")
    assert auth_client.get("/api/auth/me").status_code == 401


def test_secure_cookie_configuration_and_attributes(auth_client, monkeypatch):
    monkeypatch.setattr(
        "app.api.auth.get_settings",
        lambda: SimpleNamespace(session_cookie_secure=True),
    )
    csrf = auth_client.get("/api/auth/csrf")
    assert csrf.status_code == 200
    headers = csrf.headers.get_list("set-cookie")
    session_cookie = next(value.lower() for value in headers if COOKIE_NAME in value)
    csrf_cookie = next(value.lower() for value in headers if CSRF_COOKIE_NAME in value)
    assert "secure" in session_cookie
    assert "httponly" in session_cookie
    assert "samesite=lax" in session_cookie
    assert "path=/" in session_cookie
    assert "secure" in csrf_cookie
    assert "httponly" not in csrf_cookie


def test_bad_known_password_and_inactive_account_are_denied(auth_client, page_sessions):
    csrf = auth_client.get("/api/auth/csrf").json()["csrf_token"]
    wrong_password = auth_client.post(
        "/api/auth/login",
        json={"username": "test-admin", "password": "wrong-password"},
        headers={"X-CSRF-Token": csrf},
    )
    assert wrong_password.status_code == 401
    with page_sessions.begin() as session:
        user = session.scalar(select(User).where(User.username == "test-reader"))
        assert user is not None
        user.is_active = False
    csrf = auth_client.get("/api/auth/csrf").json()["csrf_token"]
    inactive = auth_client.post(
        "/api/auth/login",
        json={"username": "test-reader", "password": "test-password-123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert inactive.status_code == 401


def test_invalid_password_input_is_not_echoed(auth_client):
    csrf = auth_client.get("/api/auth/csrf").json()["csrf_token"]
    secret = "invalid-password-input-value"
    response = auth_client.post(
        "/api/auth/login",
        json={"username": "test-admin", "password": secret * 12},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 422
    assert secret not in response.text


def test_login_rejects_unknown_fields_without_echoing_password(auth_client):
    csrf = auth_client.get("/api/auth/csrf").json()["csrf_token"]
    secret = "sensitive-test-value"
    response = auth_client.post(
        "/api/auth/login",
        json={"username": "test-admin", "password": secret, "unexpected": "x"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 422
    assert secret not in response.text


def test_login_finds_legacy_mixed_case_username(auth_client, page_sessions):
    with page_sessions.begin() as session:
        user = session.scalar(select(User).where(User.username == "test-admin"))
        assert user is not None
        user.username = "Legacy.Admin"

    csrf = auth_client.get("/api/auth/csrf").json()["csrf_token"]
    response = auth_client.post(
        "/api/auth/login",
        json={"username": "legacy.admin", "password": "test-password-123"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 200
    assert response.json()["username"] == "Legacy.Admin"
