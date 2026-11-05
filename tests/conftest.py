"""PostgreSQL-only integration database for the bootstrap tests."""

from collections.abc import Iterator
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine, delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session, sessionmaker

from app.auth.sessions import hash_password
from app.config import get_settings
from app.db import get_session
from app.main import app
from app.models.auth_session import AuthSession
from app.models.user import User, UserRole


@pytest.fixture(scope="session")
def integration_engine() -> Iterator[Engine]:
    """Create and later remove a uniquely named database owned by this test run."""
    application_url = make_url(get_settings().database_url)
    administrative_engine = create_engine(
        application_url.set(database="postgres"), isolation_level="AUTOCOMMIT"
    )
    database_name = f"miniwiki_test_{uuid4().hex}"
    quoted_name = administrative_engine.dialect.identifier_preparer.quote(database_name)
    try:
        with administrative_engine.connect() as connection:
            connection.exec_driver_sql(f"CREATE DATABASE {quoted_name}")

        test_engine = create_engine(application_url.set(database=database_name))
        try:
            alembic_config = Config("alembic.ini")
            with test_engine.begin() as connection:
                alembic_config.attributes["connection"] = connection
                command.upgrade(alembic_config, "head")
            yield test_engine
        finally:
            test_engine.dispose()
    finally:
        with administrative_engine.connect() as connection:
            connection.exec_driver_sql(f"DROP DATABASE IF EXISTS {quoted_name}")
        administrative_engine.dispose()


@pytest.fixture
def user_sessions(integration_engine: Engine) -> Iterator[sessionmaker[Session]]:
    """Return a session factory after clearing only the run-owned test database."""
    with integration_engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM users")
    factory = sessionmaker(integration_engine, expire_on_commit=False)
    yield factory
    with integration_engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM users")


@pytest.fixture
def page_sessions(integration_engine: Engine) -> Iterator[sessionmaker[Session]]:
    """Return a clean session factory for page integration tests."""
    with integration_engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM pages")
    factory = sessionmaker(integration_engine, expire_on_commit=False)
    yield factory
    with integration_engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM pages")


@pytest.fixture
def auth_client(page_sessions: sessionmaker[Session]) -> Iterator[TestClient]:
    """Provide a guest client with deterministic test accounts."""

    def override_session() -> Iterator[Session]:
        with page_sessions() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    encoded = hash_password("test-password-123")
    with page_sessions.begin() as session:
        session.execute(delete(AuthSession))
        session.execute(delete(User))
        session.add_all(
            [
                User(
                    username=f"test-{role.value}",
                    first_name="Test",
                    last_name=role.value.title(),
                    password_hash=encoded,
                    role=role,
                    is_active=True,
                )
                for role in UserRole
            ]
        )
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_session, None)


def login_as(
    client: TestClient, username: str, password: str = "test-password-123"
) -> None:
    """Complete CSRF-protected login and retain the fresh CSRF header."""
    client.cookies.clear()
    client.headers.pop("X-CSRF-Token", None)
    token = client.get("/api/auth/csrf").json()["csrf_token"]
    result = client.post(
        "/api/auth/login",
        json={"username": username, "password": password},
        headers={"X-CSRF-Token": token},
    )
    assert result.status_code == 200, result.text
    client.headers["X-CSRF-Token"] = client.get("/api/auth/csrf").json()["csrf_token"]


@pytest.fixture
def wiki_client(auth_client: TestClient) -> Iterator[TestClient]:
    """Provide an authenticated admin client for legacy CRUD/search tests."""
    login_as(auth_client, "test-admin")
    yield auth_client
