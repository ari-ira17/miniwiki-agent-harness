"""Tests for the database readiness endpoint."""

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app


def test_health_returns_ok_when_database_is_available(monkeypatch) -> None:
    monkeypatch.setattr("app.main.check_database", lambda: None)

    response = TestClient(app).get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_returns_generic_unavailable_when_database_fails(monkeypatch) -> None:
    def fail_connection() -> None:
        raise OperationalError("secret connection details", {}, RuntimeError("secret"))

    monkeypatch.setattr("app.main.check_database", fail_connection)

    response = TestClient(app).get("/health")

    assert response.status_code == 503
    assert response.json() == {"status": "unavailable"}
    assert "secret" not in response.text


def test_openapi_documents_unavailable_status() -> None:
    schema = TestClient(app).get("/openapi.json").json()

    assert "503" in schema["paths"]["/health"]["get"]["responses"]
