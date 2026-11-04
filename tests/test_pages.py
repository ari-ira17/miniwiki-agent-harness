"""Page CRUD API and hierarchy integration tests against PostgreSQL."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from app.db import get_session
from app.main import app
from app.models.page import Page
from app.schemas.pages import PageCreate
from app.services.pages import PagePathConflict, create_page


@pytest.fixture
def page_client(page_sessions: sessionmaker[Session]) -> Iterator[TestClient]:
    """Provide an API client backed by this test's isolated PostgreSQL database."""

    def override_session() -> Iterator[Session]:
        with page_sessions() as session:
            yield session

    app.dependency_overrides[get_session] = override_session
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_session, None)


def _create_page(client: TestClient, path: str, title: str) -> dict:
    response = client.post(
        "/api/pages", json={"path": path, "title": title, "markdown": "# Notes"}
    )
    assert response.status_code == 201
    return response.json()


def test_page_crud_path_lookup_and_immutable_path(page_client: TestClient) -> None:
    created = _create_page(page_client, "/docs/nlp", "  NLP course  ")
    assert created["title"] == "NLP course"
    assert created["is_public"] is False
    assert created["author_id"] is None
    assert created["path"] == "/docs/nlp"
    assert created["created_at"].endswith("Z") or "+00:00" in created["created_at"]

    fetched = page_client.get(f"/api/pages/{created['id']}")
    assert fetched.status_code == 200
    assert fetched.json() == created
    by_path = page_client.get("/api/pages/by-path", params={"path": "/docs/nlp"})
    assert by_path.status_code == 200
    assert by_path.json()["id"] == created["id"]

    updated = page_client.patch(
        f"/api/pages/{created['id']}", json={"markdown": "Revised", "is_public": True}
    )
    assert updated.status_code == 200
    assert updated.json()["markdown"] == "Revised"
    assert updated.json()["is_public"] is True
    assert updated.json()["path"] == "/docs/nlp"

    assert (
        page_client.patch(
            f"/api/pages/{created['id']}", json={"path": "/new/path"}
        ).status_code
        == 422
    )
    assert page_client.patch(f"/api/pages/{created['id']}", json={}).status_code == 422
    assert page_client.delete(f"/api/pages/{created['id']}").status_code == 204
    assert page_client.get(f"/api/pages/{created['id']}").status_code == 404


def test_create_conflict_unknown_fields_and_not_found(page_client: TestClient) -> None:
    _create_page(page_client, "/docs/nlp", "Course")
    duplicate = page_client.post(
        "/api/pages", json={"path": "/docs/nlp", "title": "Duplicate"}
    )
    assert duplicate.status_code == 409
    assert (
        page_client.post(
            "/api/pages", json={"path": "/docs/other", "title": "Other", "author_id": 1}
        ).status_code
        == 422
    )
    assert page_client.get("/api/pages/999999").status_code == 404
    assert (
        page_client.get(
            "/api/pages/by-path", params={"path": "/missing/page"}
        ).status_code
        == 404
    )


def test_create_maps_unique_path_race_to_conflict(page_sessions) -> None:
    session = page_sessions()
    session.add(Page(path="/docs/raced", title="Existing", markdown=""))
    session.commit()

    # Model a concurrent insert after the service precheck but before its INSERT.
    session.scalar = lambda _statement: None
    with pytest.raises(PagePathConflict):
        create_page(session, PageCreate(path="/docs/raced", title="Race"))
    session.close()


def test_create_does_not_map_other_integrity_errors(page_sessions) -> None:
    session = page_sessions()

    def violate_foreign_key(db_session, _flush_context, _instances) -> None:
        for instance in db_session.new:
            if getattr(instance, "path", None) == "/docs/invalid-author":
                instance.author_id = 999999

    event.listen(session, "before_flush", violate_foreign_key)
    try:
        with pytest.raises(IntegrityError) as error:
            create_page(
                session,
                PageCreate(path="/docs/invalid-author", title="Invalid author"),
            )
        assert not isinstance(error.value, PagePathConflict)
    finally:
        event.remove(session, "before_flush", violate_foreign_key)
        session.close()


def test_list_is_paginated_and_ordered(page_client: TestClient) -> None:
    _create_page(page_client, "/docs/zeta", "Zeta")
    _create_page(page_client, "/docs/alpha", "Alpha")

    response = page_client.get("/api/pages", params={"limit": 1, "offset": 0})
    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert [item["path"] for item in response.json()["items"]] == ["/docs/alpha"]
    assert page_client.get("/api/pages", params={"limit": 101}).status_code == 422


def test_deleting_page_preserves_descendant(page_client: TestClient) -> None:
    parent = _create_page(page_client, "/docs/nlp", "Course")
    child = _create_page(page_client, "/docs/nlp/intro", "Introduction")

    assert page_client.delete(f"/api/pages/{parent['id']}").status_code == 204
    response = page_client.get(f"/api/pages/{child['id']}")
    assert response.status_code == 200
    assert response.json()["path"] == "/docs/nlp/intro"
