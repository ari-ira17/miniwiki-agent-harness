"""Export authorization, archive fidelity and path safety."""

import json
from io import BytesIO
from types import SimpleNamespace
from zipfile import ZipFile

import pytest
from sqlalchemy import update

from app.models.page import Page
from app.services.export import ExportPathConflict, build_export
from tests.conftest import login_as


def test_export_access_and_navigation(auth_client):
    assert auth_client.get("/api/export").status_code == 401
    response = auth_client.get("/export", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/login"
    for role in ("reader", "editor"):
        login_as(auth_client, f"test-{role}")
        assert auth_client.get("/api/export").status_code == 403
        assert auth_client.get("/export").status_code == 403
        assert 'href="/export"' not in auth_client.get("/").text
    login_as(auth_client, "test-admin")
    assert 'href="/export"' in auth_client.get("/").text
    for path in ("/api/export", "/export"):
        response = auth_client.get(path)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/zip"
        assert (
            response.headers["content-disposition"]
            == 'attachment; filename="miniwiki-export.zip"'
        )
        assert response.headers["cache-control"] == "no-store"
        with ZipFile(BytesIO(response.content)) as archive:
            assert archive.namelist() == []


def test_export_content_and_paths(wiki_client):
    markdown = "# Исходный текст\r\n\n```\n---\n```\n"
    pages = [
        {"path": "/docs", "title": "Родитель", "markdown": "", "tags": ["public"]},
        {
            "path": "/docs/nlp",
            "title": 'Курс "NLP"\nстрока\x7f\x85\u2028\u2029\ufffe\uffff 😀',
            "markdown": markdown,
            "tags": ['цитата"', "private"],
        },
        {"path": "/con", "title": "Reserved", "markdown": "body", "tags": []},
        {
            "path": "/virtual/branch/page",
            "title": "Без родителя",
            "markdown": markdown,
            "tags": [],
        },
    ]
    for page in pages:
        result = wiki_client.post("/api/pages", json=page)
        assert result.status_code == 201, result.text
    response = wiki_client.get("/api/export")
    with ZipFile(BytesIO(response.content)) as archive:
        assert set(archive.namelist()) == {
            "docs.md",
            "docs/nlp.md",
            "con.md",
            "virtual/branch/page.md",
        }
        for page in pages:
            content = archive.read(page["path"][1:] + ".md")
            metadata, body = content.split(b"\n---\n", 1)
            if page["path"] == "/docs/nlp":
                for char in "\x7f\x85\u2028\u2029\ufffe\uffff":
                    assert char.encode("utf-8") not in metadata
                assert "Курс".encode() in metadata
                assert "😀".encode() in metadata
            lines = metadata.decode("utf-8").splitlines()
            assert lines[0] == "---"
            assert json.loads(lines[1].removeprefix("title: ")) == page["title"]
            assert set(json.loads(lines[2].removeprefix("tags: "))) == set(page["tags"])
            assert body == page["markdown"].encode("utf-8")


@pytest.mark.parametrize("path", ["/../secret", "/docs//bad", "/docs\\evil", "/Docs"])
def test_rejects_tampered_persisted_path(wiki_client, page_sessions, path):
    assert (
        wiki_client.post(
            "/api/pages", json={"path": "/safe", "title": "Secret"}
        ).status_code
        == 201
    )
    with page_sessions.begin() as session:
        session.execute(update(Page).where(Page.path == "/safe").values(path=path))
    for endpoint in ("/api/export", "/export"):
        response = wiki_client.get(endpoint)
        assert response.status_code == 409
        assert response.json() == {"detail": "Export unavailable."}
        assert "application/zip" not in response.headers["content-type"]


def test_duplicate_archive_names_are_rejected():
    page = SimpleNamespace(path="/duplicate", title="Title", tag_names=[], markdown="")

    class Result:
        def unique(self):
            return self

        def all(self):
            return [page, page]

    class Session:
        def scalars(self, _query):
            return Result()

    with pytest.raises(ExportPathConflict):
        build_export(Session())
