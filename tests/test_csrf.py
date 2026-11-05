"""CSRF token binding and state-changing endpoint checks."""

from tests.conftest import login_as


def test_login_requires_a_token_bound_to_the_anonymous_session(auth_client):
    auth_client.get("/api/auth/csrf")
    missing = auth_client.post(
        "/api/auth/login",
        json={"username": "test-admin", "password": "test-password-123"},
    )
    assert missing.status_code == 403
    mismatch = auth_client.post(
        "/api/auth/login",
        json={"username": "test-admin", "password": "test-password-123"},
        headers={"X-CSRF-Token": "wrong-token"},
    )
    assert mismatch.status_code == 403


def test_guest_mutation_and_preview_require_authentication(auth_client):
    assert (
        auth_client.post(
            "/api/pages", json={"path": "/guest", "title": "No"}
        ).status_code
        == 401
    )
    assert (
        auth_client.post("/api/markdown/preview", json={"markdown": "No"}).status_code
        == 401
    )


def test_cookie_authenticated_writes_require_csrf(auth_client):
    login_as(auth_client, "test-admin")
    token = auth_client.headers.pop("X-CSRF-Token")
    response = auth_client.post(
        "/api/pages", json={"path": "/csrf-check", "title": "Check"}
    )
    assert response.status_code == 403
    auth_client.headers["X-CSRF-Token"] = token
    assert (
        auth_client.post(
            "/api/pages", json={"path": "/csrf-check", "title": "Check"}
        ).status_code
        == 201
    )


def test_missing_and_wrong_csrf_block_preview_patch_delete_and_logout(auth_client):
    login_as(auth_client, "test-admin")
    created = auth_client.post(
        "/api/pages",
        json={"path": "/csrf-complete", "title": "CSRF"},
        headers={"X-CSRF-Token": auth_client.headers["X-CSRF-Token"]},
    ).json()
    auth_client.get("/api/auth/csrf")
    for method, path, payload in (
        ("post", "/api/markdown/preview", {"markdown": "test"}),
        ("patch", f"/api/pages/{created['id']}", {"title": "changed"}),
        ("delete", f"/api/pages/{created['id']}", None),
        ("post", "/api/auth/logout", None),
    ):
        auth_client.headers.pop("X-CSRF-Token", None)
        request = getattr(auth_client, method)
        kwargs = {"json": payload} if payload is not None else {}
        assert request(path, **kwargs).status_code == 403
        assert (
            request(path, **kwargs, headers={"X-CSRF-Token": "wrong"}).status_code
            == 403
        )


def test_bad_credentials_are_generic_and_password_is_not_reflected(auth_client):
    csrf = auth_client.get("/api/auth/csrf").json()["csrf_token"]
    response = auth_client.post(
        "/api/auth/login",
        json={"username": "unknown-user", "password": "sensitive-test-value"},
        headers={"X-CSRF-Token": csrf},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid username or password."
    assert "sensitive-test-value" not in response.text


def test_non_ascii_csrf_input_is_rejected_without_server_error(auth_client):
    login_as(auth_client, "test-admin")
    response = auth_client.post("/api/auth/logout", headers={b"X-CSRF-Token": b"\xe9"})
    assert response.status_code == 403
