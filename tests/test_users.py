"""Admin user management API, password privacy and lock safety."""

from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session, sessionmaker

from app.auth.sessions import hash_password
from app.models.auth_session import AuthSession
from app.models.user import User, UserRole
from app.schemas.users import UserUpdate
from app.services import users as user_service
from tests.conftest import login_as


def _csrf(client: TestClient) -> dict[str, str]:
    return {"X-CSRF-Token": client.get("/api/auth/csrf").json()["csrf_token"]}


def test_only_admin_can_access_user_management(auth_client: TestClient) -> None:
    login_as(auth_client, "test-editor")
    assert auth_client.get("/api/users").status_code == 403
    assert auth_client.get("/users", follow_redirects=False).status_code == 403
    assert auth_client.post("/api/users", json={}).status_code == 403

    login_as(auth_client, "test-reader")
    assert auth_client.get("/api/users").status_code == 403
    assert auth_client.get("/users", follow_redirects=False).status_code == 403


def test_admin_can_create_list_update_deactivate_and_delete_users(
    auth_client: TestClient,
) -> None:
    login_as(auth_client, "test-admin")
    listed = auth_client.get("/api/users")
    assert listed.status_code == 200
    assert "password_hash" not in listed.text
    assert "test-admin" in {item["username"] for item in listed.json()}

    created = auth_client.post(
        "/api/users",
        json={
            "username": "  New.Editor ",
            "first_name": "  New ",
            "last_name": "Editor",
            "password": "secure-initial-456",
            "role": "editor",
        },
        headers=_csrf(auth_client),
    )
    assert created.status_code == 201, created.text
    account = created.json()
    assert account == {
        "id": account["id"],
        "username": "new.editor",
        "first_name": "New",
        "last_name": "Editor",
        "full_name": "New Editor",
        "role": "editor",
        "is_active": True,
    }
    assert "secure-initial-456" not in created.text
    assert "password_hash" not in created.text

    duplicate = auth_client.post(
        "/api/users",
        json={
            "username": "NEW.EDITOR",
            "first_name": "New",
            "last_name": "Editor",
            "password": "secure-initial-456",
            "role": "reader",
        },
        headers=_csrf(auth_client),
    )
    assert duplicate.status_code == 409

    reader_client = TestClient(auth_client.app)
    try:
        token = reader_client.get("/api/auth/csrf").json()["csrf_token"]
        login = reader_client.post(
            "/api/auth/login",
            json={"username": account["username"], "password": "secure-initial-456"},
            headers={"X-CSRF-Token": token},
        )
        assert login.status_code == 200
        assert login.json()["role"] == "editor"
        assert reader_client.get("/api/auth/me").status_code == 200
        renamed = auth_client.patch(
            f"/api/users/{account['id']}",
            json={"first_name": "Edited", "last_name": "Profile"},
            headers=_csrf(auth_client),
        )
        assert renamed.status_code == 200
        assert renamed.json()["full_name"] == "Edited Profile"
        assert reader_client.get("/api/auth/me").json()["full_name"] == "Edited Profile"

        updated = auth_client.patch(
            f"/api/users/{account['id']}",
            json={"role": "reader", "password": "replacement-secret-678"},
            headers=_csrf(auth_client),
        )
        assert updated.status_code == 200
        assert updated.json()["role"] == "reader"
        assert "replacement-secret-678" not in updated.text
        assert reader_client.get("/api/auth/me").status_code == 401

        token = reader_client.get("/api/auth/csrf").json()["csrf_token"]
        relogin = reader_client.post(
            "/api/auth/login",
            json={
                "username": account["username"],
                "password": "replacement-secret-678",
            },
            headers={"X-CSRF-Token": token},
        )
        assert relogin.status_code == 200
        assert relogin.json()["role"] == "reader"
        deactivated = auth_client.patch(
            f"/api/users/{account['id']}",
            json={"is_active": False},
            headers=_csrf(auth_client),
        )
        assert deactivated.status_code == 200
        assert deactivated.json()["is_active"] is False
        assert reader_client.get("/api/auth/me").status_code == 401
    finally:
        reader_client.close()

    assert (
        auth_client.delete(
            f"/api/users/{account['id']}", headers=_csrf(auth_client)
        ).status_code
        == 204
    )
    assert (
        auth_client.delete(
            f"/api/users/{account['id']}", headers=_csrf(auth_client)
        ).status_code
        == 404
    )


def test_invalid_user_fields_do_not_echo_passwords(auth_client: TestClient) -> None:
    login_as(auth_client, "test-admin")
    short_secret = "tiny-secret"
    invalid = auth_client.post(
        "/api/users",
        json={
            "username": "short",
            "first_name": "Test",
            "last_name": "Reader",
            "password": short_secret,
            "role": "reader",
        },
        headers=_csrf(auth_client),
    )
    assert invalid.status_code == 422
    assert short_secret not in invalid.text
    for first_name, last_name in (
        ("", "Reader"),
        (" ", "Reader"),
        ("First", None),
        ("И\x00рина", "Reader"),
    ):
        invalid_name = auth_client.post(
            "/api/users",
            json={
                "username": "invalid-name",
                "first_name": first_name,
                "last_name": last_name,
                "password": "secure-initial-456",
                "role": "reader",
            },
            headers=_csrf(auth_client),
        )
        assert invalid_name.status_code == 422

    created = auth_client.post(
        "/api/users",
        json={
            "username": "change-me",
            "first_name": "Change",
            "last_name": "Me",
            "password": "secure-initial-456",
            "role": "reader",
        },
        headers=_csrf(auth_client),
    ).json()
    too_long_secret = "too-long-secret-value"
    invalid_patch = auth_client.patch(
        f"/api/users/{created['id']}",
        json={"password": too_long_secret * 20},
        headers=_csrf(auth_client),
    )
    assert invalid_patch.status_code == 422
    assert too_long_secret not in invalid_patch.text
    assert (
        auth_client.patch(
            f"/api/users/{created['id']}",
            json={"username": "new-name"},
            headers=_csrf(auth_client),
        ).status_code
        == 422
    )
    assert (
        auth_client.patch(
            f"/api/users/{created['id']}",
            json={"password": None},
            headers=_csrf(auth_client),
        ).status_code
        == 422
    )
    assert (
        auth_client.patch(
            f"/api/users/{created['id']}",
            json={"first_name": "  "},
            headers=_csrf(auth_client),
        ).status_code
        == 422
    )


def test_user_creation_conflicts_with_case_insensitive_legacy_name(
    auth_client: TestClient, page_sessions: sessionmaker[Session]
) -> None:
    login_as(auth_client, "test-admin")
    with page_sessions.begin() as session:
        session.add(
            User(
                username="Legacy.User",
                first_name="Legacy",
                last_name="User",
                password_hash=hash_password("secure-initial-456"),
                role=UserRole.READER,
                is_active=True,
            )
        )

    response = auth_client.post(
        "/api/users",
        json={
            "username": "legacy.user",
            "first_name": "Legacy",
            "last_name": "User",
            "password": "secure-initial-789",
            "role": "editor",
        },
        headers=_csrf(auth_client),
    )
    assert response.status_code == 409
    with page_sessions() as session:
        matches = list(
            session.scalars(select(User).where(User.username.ilike("legacy.user")))
        )
    assert [match.username for match in matches] == ["Legacy.User"]


def test_last_active_admin_cannot_be_demoted_disabled_or_deleted(
    auth_client: TestClient,
) -> None:
    login_as(auth_client, "test-admin")
    admin_id = auth_client.get("/api/auth/me").json()["id"]
    assert (
        auth_client.patch(
            f"/api/users/{admin_id}",
            json={"role": "editor"},
            headers=_csrf(auth_client),
        ).status_code
        == 409
    )
    assert (
        auth_client.patch(
            f"/api/users/{admin_id}",
            json={"is_active": False},
            headers=_csrf(auth_client),
        ).status_code
        == 409
    )
    assert (
        auth_client.delete(
            f"/api/users/{admin_id}", headers=_csrf(auth_client)
        ).status_code
        == 409
    )
    assert auth_client.get("/api/auth/me").status_code == 200


def test_parallel_admin_demotion_leaves_one_active_admin(
    user_sessions: sessionmaker[Session],
) -> None:
    encoded = hash_password("parallel-test-password")
    with user_sessions.begin() as session:
        session.add_all(
            [
                User(
                    username="admin-a",
                    first_name="Admin",
                    last_name="A",
                    password_hash=encoded,
                    role=UserRole.ADMIN,
                    is_active=True,
                ),
                User(
                    username="admin-b",
                    first_name="Admin",
                    last_name="B",
                    password_hash=encoded,
                    role=UserRole.ADMIN,
                    is_active=True,
                ),
            ]
        )
    with user_sessions() as session:
        ids = dict(session.execute(select(User.username, User.id)).all())

    barrier = Barrier(2)

    def demote(actor: str, target: str) -> str:
        with user_sessions() as session:
            barrier.wait()
            try:
                user_service.update_user(
                    session,
                    ids[actor],
                    ids[target],
                    UserUpdate(role=UserRole.EDITOR),
                )
                return "updated"
            except user_service.ActorNoLongerAdmin:
                session.rollback()
                return "authority-lost"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(
            pool.map(
                lambda pair: demote(*pair),
                [("admin-a", "admin-b"), ("admin-b", "admin-a")],
            )
        )
    assert sorted(results) == ["authority-lost", "updated"]
    with user_sessions() as session:
        active_admins = session.scalar(
            select(func.count())
            .select_from(User)
            .where(User.role == UserRole.ADMIN, User.is_active.is_(True))
        )
    assert active_admins == 1


def test_user_role_and_password_change_revoke_all_sessions(auth_client, page_sessions):
    login_as(auth_client, "test-admin")
    user = auth_client.post(
        "/api/users",
        json={
            "username": "session-revoke",
            "first_name": "Session",
            "last_name": "Revoke",
            "password": "secure-initial-456",
            "role": "reader",
        },
        headers=_csrf(auth_client),
    ).json()
    reader = TestClient(auth_client.app)
    try:
        token = reader.get("/api/auth/csrf").json()["csrf_token"]
        assert (
            reader.post(
                "/api/auth/login",
                json={"username": user["username"], "password": "secure-initial-456"},
                headers={"X-CSRF-Token": token},
            ).status_code
            == 200
        )
        with page_sessions() as session:
            assert (
                session.scalar(
                    select(func.count())
                    .select_from(AuthSession)
                    .where(AuthSession.user_id == user["id"])
                )
                == 1
            )
        changed = auth_client.patch(
            f"/api/users/{user['id']}",
            json={"role": "editor"},
            headers=_csrf(auth_client),
        )
        assert changed.status_code == 200
        assert reader.get("/api/auth/me").status_code == 401
    finally:
        reader.close()
