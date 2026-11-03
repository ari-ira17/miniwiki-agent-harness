"""Tests for the public service shell, which contains no wiki content."""

from fastapi.testclient import TestClient

from app.main import app


def test_root_renders_russian_service_shell() -> None:
    response = TestClient(app).get("/")

    assert response.status_code == 200
    assert "Добро пожаловать в MiniWiki" in response.text
    assert "Локальный прототип" in response.text
    assert "Не размещайте сервис в открытой сети." in response.text
    assert '<html lang="ru">' in response.text


def test_app_start_runs_bootstrap_before_serving_requests(monkeypatch) -> None:
    sentinel_factory = object()
    called_with = []
    monkeypatch.setattr("app.main.get_session_factory", lambda: sentinel_factory)
    monkeypatch.setattr(
        "app.main.ensure_initial_admin", lambda factory: called_with.append(factory)
    )

    with TestClient(app) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert called_with == [sentinel_factory]


def test_shell_stylesheet_is_available() -> None:
    response = TestClient(app).get("/static/styles.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]


def test_private_source_files_are_not_served() -> None:
    client = TestClient(app)

    assert client.get("/app/config.py").status_code == 404
    assert client.get("/static/%2e%2e/.env").status_code == 404
    assert client.get("/articles/private").status_code == 404
