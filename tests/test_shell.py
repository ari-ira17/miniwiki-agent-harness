"""Tests for the public service shell, which contains no wiki content."""

from fastapi.testclient import TestClient

from app.main import app


def test_root_opens_russian_login_shell_for_guests() -> None:
    client = TestClient(app)
    redirect = client.get("/", follow_redirects=False)
    assert redirect.status_code == 303
    assert redirect.headers["location"] == "/login"
    response = client.get(redirect.headers["location"])

    assert response.status_code == 200
    assert '<h1 id="login-title">Вход</h1>' in response.text
    assert "data-login-form" in response.text
    assert "Бакалавриат" not in response.text
    assert 'aria-label="Основная навигация">' in response.text
    assert 'href="/pages/new"' not in response.text
    assert '<html lang="ru">' in response.text
    assert 'href="/pages">Страницы</a>' not in response.text
    assert "data-sidebar-toggle" in response.text
    assert 'aria-controls="wiki-sidebar"' in response.text
    assert "/static/navigation.js" in response.text


def test_sidebar_navigation_script_is_served() -> None:
    response = TestClient(app).get("/static/navigation.js")

    assert response.status_code == 200
    assert "sidebar-collapsed" in response.text
    assert "aria-expanded" in response.text


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
