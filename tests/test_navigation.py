"""Role-visible page tree and sanitized article outline integration tests."""

import re
from html import unescape

from fastapi.testclient import TestClient
from sqlalchemy import select

from app.course_samples import COURSES
from app.demo import seed_demo
from app.models.page import Page
from app.services.markdown import render_document
from tests.conftest import login_as


def test_course_catalog_and_imported_material_contract(auth_client: TestClient) -> None:
    assert (
        auth_client.get("/wiki/disciplines/nlp", follow_redirects=False).status_code
        == 303
    )
    login_as(auth_client, "test-reader")
    home = auth_client.get("/")
    assert home.status_code == 200
    assert "Учебные дисциплины" in home.text
    assert "Бакалавриат" in home.text
    assert "Магистратура" in home.text
    assert "Элективные дисциплины" in home.text
    assert "КАТАЛОГ" not in home.text
    assert "Каталог дисциплин" not in home.text
    assert 'aria-label="Разделы дисциплин"' in home.text
    course_links = re.findall(r'href="(/wiki/disciplines/[^\"]+)"', home.text)
    assert course_links == [
        "/wiki/disciplines/programming-workshop-bachelors-5sem",
        "/wiki/disciplines/nlp",
    ]

    course_pages = {page.path: page for page in COURSES}
    nlp = course_pages["/disciplines/nlp"]
    practice = course_pages["/disciplines/programming-workshop-bachelors-5sem"]
    preprocessing = course_pages["/disciplines/nlp/lectures/preprocessing"]
    assert nlp.tags == ["public", "nlp", "deep learning", "machine learning"]
    assert practice.tags == ["public", "machine learning"]
    nlp_links = re.findall(r"\]\(([^)]+)\)", nlp.markdown)
    assert set(nlp_links) <= {
        "/wiki/disciplines/nlp",
        "/wiki/disciplines/nlp/lectures/preprocessing",
    }
    practice_links = re.findall(r"\]\(([^)]+)\)", practice.markdown)
    assert [
        href for href in practice_links if href.startswith(("http:", "https:"))
    ] == [
        "https://docs.google.com/presentation/d/1tKrjcpheXF5vQyi5oCrYbrh4LJ5tuCstLkMo1bchjN0/edit?usp=sharing"
    ]
    dataset_section = practice.markdown.split("## Варианты датасетов", 1)[1].split(
        "## Лабораторные работы (50 баллов)", 1
    )[0]
    dataset_rows = [
        line for line in dataset_section.splitlines() if line.startswith("| ")
    ]
    assert len(dataset_rows) == 14
    assert sum("✅" in line for line in dataset_rows) == 13
    assert len(re.findall(r"(?m)^```", preprocessing.markdown)) == 32
    regex_table = preprocessing.markdown.split(
        "### Основные элементы регулярных выражений", 1
    )[1].split("### Удаление URL и email", 1)[0]
    assert (
        sum(
            line.startswith("| ") and line.count("|") >= 3
            for line in regex_table.splitlines()
        )
        == 22
    )
    assert preprocessing.markdown.count("</w>") == 13
    assert not preprocessing.markdown.startswith("# ")
    symbol_rows = [
        line
        for line in regex_table.splitlines()
        if line.startswith("| ") and line.count("|") >= 4
    ][1:]
    assert len(symbol_rows) == 21
    assert [line.split(" | ", 2)[1] for line in symbol_rows][-1] == "`\\|`"
    rendered_markdown, _ = render_document(preprocessing.markdown)
    rendered_table = re.search(r"<table>.*?</table>", rendered_markdown, re.DOTALL)
    assert rendered_table is not None
    cells = [
        unescape(re.sub(r"<[^>]+>", "", cell))
        for cell in re.findall(r"<td>(.*?)</td>", rendered_table.group())
    ]
    assert len(cells) == 21 * 4
    assert cells[1::4] == [
        "a, 1, !",
        ".",
        "\\",
        "[...]",
        "[^...]",
        "\\d",
        "\\D",
        "\\w",
        "\\W",
        "\\s",
        "\\S",
        "^",
        "$",
        "*",
        "+",
        "?",
        "{n}",
        "{n,}",
        "{n,m}",
        "(...)",
        "|",
    ]
    assert r"<td><code>\</code></td>" in rendered_markdown
    assert "<td><code>|</code></td>" in rendered_markdown


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


def test_article_toc_stays_separate_from_sidebar_and_heading_xss_matches_preview(
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
    assert 'aria-label="Навигационная цепочка"' not in article.text
    assert 'class="breadcrumbs"' not in article.text
    assert 'aria-label="Оглавление статьи"' in article.text
    assert article.text.count('href="#article-повтор"') == 1
    assert article.text.count('href="#article-повтор-2"') == 1
    tree = article.text.split('aria-label="Дерево страниц"', 1)[1].split("</nav>", 1)[0]
    assert 'aria-current="page"' in tree
    assert "docs" in tree and "nlp" in tree
    assert 'class="tree-icon" aria-hidden="true" viewBox="0 0 20 20"' in tree
    assert "Повтор" not in tree
    assert "article-повтор" not in tree


def test_course_tree_shows_local_pages_without_markdown_outline(
    auth_client: TestClient,
) -> None:
    login_as(auth_client, "test-admin")
    pages = (
        {
            "path": "/disciplines/nlp",
            "title": "Course root",
            "markdown": "# Course heading",
        },
        {
            "path": "/disciplines/nlp/lectures",
            "title": "Lecture collection",
        },
        {
            "path": "/disciplines/nlp/lectures/preprocessing",
            "title": "Local lecture title",
            "markdown": "## Lecture subsection",
        },
        {
            "path": "/disciplines/nlp/notes/part",
            "title": "Nested course note",
        },
        {
            "path": "/disciplines/programming-workshop-bachelors-5sem",
            "title": "Practice root",
        },
    )
    for page in pages:
        assert auth_client.post("/api/pages", json=page).status_code == 201

    response = auth_client.get("/wiki/disciplines/nlp/lectures/preprocessing")
    assert response.status_code == 200
    tree = response.text.split('aria-label="Дерево страниц"', 1)[1].split("</nav>", 1)[
        0
    ]
    assert re.search(r'data-tree-title="Бакалавриат"[^>]*aria-expanded="true"', tree)
    assert re.search(r'data-tree-title="3 курс"[^>]*aria-expanded="true"', tree)
    assert 'data-tree-title="Course root"' in tree
    assert 'data-tree-title="Practice root"' in tree
    assert "Основная страница" in tree
    assert "Лекции" in tree
    assert "Local lecture title" in tree
    assert "Lecture collection" in tree
    assert "Lecture subsection" not in tree
    assert 'href="/wiki/disciplines/nlp/lectures/preprocessing#article-' not in tree
    assert ">notes<" in tree
    assert 'href="/wiki/disciplines/nlp/notes/part"' in tree
    assert 'href="/wiki/disciplines/nlp/disciplines/nlp/' not in tree
    assert "/#" not in tree
    assert (
        "Lecture subsection"
        in response.text.split('aria-label="Оглавление статьи"', 1)[1].split(
            "</nav>", 1
        )[0]
    )
    home = auth_client.get("/")
    home_tree = home.text.split('aria-label="Дерево страниц"', 1)[1].split("</nav>", 1)[
        0
    ]
    assert re.search(
        r'data-tree-title="Бакалавриат"[^>]*aria-expanded="true"', home_tree
    )
    assert re.search(r'data-tree-title="3 курс"[^>]*aria-expanded="true"', home_tree)
    assert "Лекции отсутствуют" in home_tree
    assert 'href="/wiki/disciplines/nlp/lectures"' in home_tree


def test_empty_database_has_clear_empty_state(wiki_client: TestClient) -> None:
    page = wiki_client.get("/pages")
    assert page.status_code == 200
    assert "Пока нет страниц" in page.text
    assert "Создать первую страницу" in page.text
    assert "Бакалавриат" in page.text
    assert "Магистратура" in page.text


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
            "markdown": "# Секретный заголовок",
            "tags": ["classified"],
        },
    ).json()
    child = wiki_client.post(
        "/api/pages",
        json={
            "path": "/secret-section/public-child",
            "title": "Открытая статья",
            "is_public": True,
            "tags": ["open-child", "public"],
        },
    ).json()
    login_as(wiki_client, "test-reader")
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
        assert wiki_client.get("/api/tags").json() == ["open-child", "public"]
        tree_html = wiki_client.get("/pages").text
        assert "Тайный раздел" not in tree_html
        assert "Секретный заголовок" not in tree_html
        article = wiki_client.get(f"/wiki{child['path']}").text
        assert "Тайный раздел" not in article
        assert "secret-section" in article
    finally:
        pass
