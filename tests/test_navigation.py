"""Page tree, breadcrumbs and sanitized article outline integration tests."""

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.api.pages import get_page_scope
from app.demo import seed_demo
from app.models.page import Page
from app.services.permissions import public_pages_scope


def test_tree_has_virtual_branches_and_html_search_empty_states(
    wiki_client: TestClient,
) -> None:
    created = wiki_client.post(
        "/api/pages",
        json={
            "path": "/course/linguistics/search",
            "title": "Поиск по корпусу",
            "tags": ["nlp"],
        },
    ).json()
    tree = wiki_client.get("/api/navigation/tree")
    assert tree.status_code == 200
    assert tree.json() == [
        {
            "path": "/course",
            "title": "course",
            "page_id": None,
            "children": [
                {
                    "path": "/course/linguistics",
                    "title": "linguistics",
                    "page_id": None,
                    "children": [
                        {
                            "path": "/course/linguistics/search",
                            "title": "Поиск по корпусу",
                            "page_id": created["id"],
                            "children": [],
                        }
                    ],
                }
            ],
        }
    ]
    listing = wiki_client.get("/pages")
    assert "Поиск по корпусу" in listing.text
    empty = wiki_client.get("/pages", params={"q": "несуществующий термин"})
    assert "Ничего не найдено" in empty.text
    assert "Сбросить фильтры" in empty.text
    assert 'aria-label="Дерево страниц"' in empty.text
    assert wiki_client.get("/pages", params={"q": "x" * 201}).status_code == 422


def test_article_toc_breadcrumbs_and_heading_xss_are_consistent_with_preview(
    wiki_client: TestClient,
) -> None:
    markdown = (
        "# Первый\n\n## Повтор\n\n## Повтор\n\n## Повтор-2"
        '\n\n### <script>alert(1)</script>\n\n<h2 id="article-stolen">Свой HTML</h2>'
    )
    created = wiki_client.post(
        "/api/pages",
        json={"path": "/docs/nlp/outline", "title": "Оглавление", "markdown": markdown},
    ).json()
    preview = wiki_client.post("/api/markdown/preview", json={"markdown": markdown})
    assert preview.status_code == 200
    assert [row["id"] for row in preview.json()["outline"]] == [
        "article-первый",
        "article-повтор",
        "article-повтор-2",
        "article-повтор-2-2",
        "article-script-alert-1-script",
    ]

    article = wiki_client.get(f"/wiki{created['path']}")
    assert article.status_code == 200
    assert preview.json()["html"] in article.text
    assert (
        'id="article-повтор"' in article.text
        and 'id="article-повтор-2"' in article.text
    )
    assert 'id="article-stolen"' not in article.text
    assert "<script>alert(1)</script>" not in article.text
    assert 'aria-label="Навигационная цепочка"' in article.text
    assert 'aria-label="Оглавление статьи"' in article.text
    assert article.text.count('href="#article-повтор"') == 1
    assert article.text.count('href="#article-повтор-2"') == 1
    # The missing /docs and /docs/nlp ancestors remain plain text breadcrumbs.
    assert "<span>docs</span>" in article.text
    assert "<span>nlp</span>" in article.text


def test_empty_database_has_clear_empty_state(wiki_client: TestClient) -> None:
    page = wiki_client.get("/pages")
    assert page.status_code == 200
    assert "Пока нет страниц" in page.text
    assert "Создать первую страницу" in page.text
    assert "Страниц пока нет" in page.text


def test_demo_seed_is_idempotent_and_does_not_overwrite(page_sessions) -> None:
    assert len(seed_demo(page_sessions)) == 4
    assert seed_demo(page_sessions) == []
    with page_sessions() as session:
        page = session.scalar(
            select(Page).where(Page.path == "/demo/linguistics/search")
        )
        assert page is not None
        page.title = "Локальное изменение"
        session.commit()
        long_page = session.scalar(
            select(Page).where(Page.path == "/demo/long-article")
        )
        assert long_page is not None
        assert len(long_page.markdown) > 10_000
    assert seed_demo(page_sessions) == []
    with page_sessions() as session:
        page = session.scalar(
            select(Page).where(Page.path == "/demo/linguistics/search")
        )
        assert page is not None
        assert page.title == "Локальное изменение"


def test_visible_child_does_not_disclose_hidden_parent_title(
    wiki_client: TestClient,
) -> None:
    hidden = wiki_client.post(
        "/api/pages",
        json={
            "path": "/secret-section",
            "title": "Тайный раздел",
            "tags": ["classified"],
        },
    ).json()
    child = wiki_client.post(
        "/api/pages",
        json={
            "path": "/secret-section/public-child",
            "title": "Открытая статья",
            "is_public": True,
            "tags": ["open-child"],
        },
    ).json()
    wiki_client.app.dependency_overrides[get_page_scope] = lambda: public_pages_scope
    try:
        tree = wiki_client.get("/api/navigation/tree").json()
        assert tree == [
            {
                "path": "/secret-section",
                "title": "secret-section",
                "page_id": None,
                "children": [
                    {
                        "path": child["path"],
                        "title": child["title"],
                        "page_id": child["id"],
                        "children": [],
                    }
                ],
            }
        ]
        assert (
            wiki_client.get("/api/pages", params={"q": "Тайный раздел"}).json()["total"]
            == 0
        )
        assert (
            wiki_client.get(
                "/api/pages/by-path", params={"path": hidden["path"]}
            ).status_code
            == 404
        )
        assert wiki_client.get("/api/tags").json() == ["open-child"]
        tree_html = wiki_client.get("/pages").text
        assert "Тайный раздел" not in tree_html
        article = wiki_client.get(f"/wiki{child['path']}").text
        assert "Тайный раздел" not in article
        assert "<span>secret-section</span>" in article
    finally:
        wiki_client.app.dependency_overrides.pop(get_page_scope, None)
