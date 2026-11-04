"""Search, tags and visibility filtering integration tests."""

from fastapi.testclient import TestClient

from app.api.pages import get_page_scope
from app.services.permissions import public_pages_scope


def test_search_matches_cyrillic_title_and_markdown_and_escapes_like(
    wiki_client: TestClient,
) -> None:
    title = wiki_client.post(
        "/api/pages",
        json={
            "path": "/course/title",
            "title": "Морфология русского языка",
            "tags": [" Nlp ", "nlp"],
        },
    ).json()
    body = wiki_client.post(
        "/api/pages",
        json={
            "path": "/course/body",
            "title": "Конспект",
            "markdown": "Важна семантика 100%_тест",
        },
    ).json()

    by_title = wiki_client.get("/api/pages", params={"q": "МОРФОЛОГИЯ"}).json()
    assert by_title["total"] == 1
    assert by_title["items"][0]["id"] == title["id"]
    by_body = wiki_client.get("/api/pages", params={"q": "СЕМАНТИКА"}).json()
    assert by_body["total"] == 1
    assert by_body["items"][0]["id"] == body["id"]
    literal = wiki_client.get("/api/pages", params={"q": "%_"}).json()
    assert [item["id"] for item in literal["items"]] == [body["id"]]
    assert title["tags"] == ["nlp"]


def test_tags_filter_pagination_and_empty_results(wiki_client: TestClient) -> None:
    first = wiki_client.post(
        "/api/pages",
        json={"path": "/a", "title": "Alpha", "tags": ["search"]},
    ).json()
    wiki_client.post(
        "/api/pages",
        json={"path": "/b", "title": "Beta", "tags": ["other"]},
    )
    wiki_client.post(
        "/api/pages",
        json={"path": "/c", "title": "Gamma", "tags": ["search"]},
    )
    results = wiki_client.get(
        "/api/pages", params={"q": "", "tag": "SEARCH", "limit": 1}
    )
    assert results.status_code == 200
    assert results.json()["total"] == 2
    assert results.json()["items"][0]["id"] == first["id"]
    assert wiki_client.get("/api/tags").json() == ["other", "search"]
    assert wiki_client.get("/api/pages", params={"q": "no match"}).json()["total"] == 0
    assert wiki_client.get("/api/pages", params={"q": "x" * 201}).status_code == 422
    assert (
        wiki_client.post(
            "/api/pages", json={"path": "/bad", "title": "Bad", "tags": ["a,b"]}
        ).status_code
        == 422
    )
    filtered_page = wiki_client.get(
        "/pages", params={"q": "a", "tag": "search", "limit": 1}
    )
    assert "q=a&amp;tag=search" in filtered_page.text
    next_page = wiki_client.get(
        "/pages", params={"q": "a", "tag": "search", "limit": 1, "offset": 1}
    )
    assert "Gamma" in next_page.text


def test_page_tags_can_be_replaced_and_access_scope_filters_totals(
    wiki_client: TestClient,
) -> None:
    visible = wiki_client.post(
        "/api/pages",
        json={
            "path": "/public",
            "title": "Visible",
            "is_public": True,
            "tags": ["open"],
        },
    ).json()
    private = wiki_client.post(
        "/api/pages",
        json={"path": "/private", "title": "Secret", "tags": ["secret"]},
    ).json()
    updated = wiki_client.patch(
        f"/api/pages/{visible['id']}", json={"tags": ["new", "NEW", "Course"]}
    )
    assert updated.status_code == 200
    assert updated.json()["tags"] == ["course", "new"]
    assert updated.json()["updated_at"] >= visible["updated_at"]
    assert wiki_client.patch(
        f"/api/pages/{visible['id']}", json={"markdown": "edited"}
    ).json()["tags"] == ["course", "new"]
    assert (
        wiki_client.patch(f"/api/pages/{visible['id']}", json={"tags": []}).json()[
            "tags"
        ]
        == []
    )
    assert (
        wiki_client.patch(
            f"/api/pages/{visible['id']}", json={"tags": None}
        ).status_code
        == 422
    )
    assert (
        wiki_client.post(
            "/api/pages",
            json={
                "path": "/too-many",
                "title": "Too many",
                "tags": [str(i) for i in range(21)],
            },
        ).status_code
        == 422
    )
    assert (
        wiki_client.post(
            "/api/pages",
            json={"path": "/too-long", "title": "Too long", "tags": ["x" * 33]},
        ).status_code
        == 422
    )
    assert wiki_client.patch(
        f"/api/pages/{visible['id']}", json={"tags": ["course", "new"]}
    ).json()["tags"] == ["course", "new"]

    wiki_client.app.dependency_overrides[get_page_scope] = lambda: public_pages_scope
    try:
        listing = wiki_client.get("/api/pages").json()
        assert listing["total"] == 1
        assert [page["id"] for page in listing["items"]] == [visible["id"]]
        assert (
            wiki_client.get("/api/pages", params={"q": "Secret"}).json()["total"] == 0
        )
        assert (
            wiki_client.get(
                "/api/pages/by-path", params={"path": "/private"}
            ).status_code
            == 404
        )
        assert wiki_client.get("/api/tags").json() == ["course", "new"]
        assert wiki_client.get("/api/tags").json().count("secret") == 0
        tree = wiki_client.get("/api/navigation/tree").json()
        assert [node["path"] for node in tree] == ["/public"]
        assert wiki_client.get(f"/api/pages/{private['id']}").status_code == 404
        hidden_search = wiki_client.get("/pages", params={"q": "Secret"})
        assert 'class="page-item-title">Secret</span>' not in hidden_search.text
        assert "secret" not in hidden_search.text
        assert "/private" not in hidden_search.text
    finally:
        wiki_client.app.dependency_overrides.pop(get_page_scope, None)
