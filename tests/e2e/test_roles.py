"""End-to-end authentication, user administration and role visibility."""

import re
from uuid import uuid4

import pytest
from playwright.sync_api import Page, expect, sync_playwright

from tests.e2e.helpers import ADMIN_PASSWORD, ADMIN_USERNAME, BASE_URL, sign_in

pytestmark = pytest.mark.e2e


def _create_page(page: Page, path: str, title: str, tags: str = "") -> None:
    page.goto(f"{BASE_URL}/pages/new")
    expect(page.get_by_role("heading", name="РЕДАКТОР MARKDOWN")).to_be_visible()
    page.get_by_label("Иерархический путь").fill(path)
    page.get_by_label("Заголовок").fill(title)
    page.get_by_label("Теги").fill(tags)
    page.get_by_label("Текст страницы (Markdown)").fill(
        f"# {title}\n\nТекст для проверки доступа."
    )
    page.get_by_role("button", name="Обновить предпросмотр").click()
    expect(
        page.locator("[data-preview-content]").get_by_role("heading", name=title)
    ).to_be_visible()
    with page.expect_navigation():
        page.get_by_role("button", name="Создать страницу").click()
    expect(page).to_have_url(f"{BASE_URL}/wiki{path}")


def test_guest_admin_editor_reader_and_session_invalidation() -> None:
    run = uuid4().hex[:8]
    editor_name = f"browser-editor-{run}"
    reader_name = f"browser-reader-{run}"
    initial_password = "Browser-initial-password-876"
    reset_password = "Browser-reset-password-987"
    secret_title = f"Private record {run}"
    child_title = f"Public descendant {run}"
    public_path = f"/roles-{run}/public"
    private_path = f"/roles-{run}/private"
    child_path = f"{private_path}/visible-child"

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            page_errors: list[str] = []
            admin = browser.new_page(viewport={"width": 1440, "height": 1000})
            admin.on("pageerror", lambda error: page_errors.append(str(error)))
            no_script = browser.new_page(java_script_enabled=False)
            catalog_response = admin.goto(f"{BASE_URL}/")
            assert catalog_response is not None and catalog_response.status == 200
            expect(
                admin.get_by_role("heading", name="Учебные дисциплины")
            ).to_be_visible()
            expect(
                admin.get_by_role(
                    "link", name="Обработка естественного языка", exact=True
                )
            ).to_have_attribute("href", "/wiki/disciplines/nlp")
            expect(
                admin.get_by_role(
                    "link", name="Практикум по программированию 5-й семестр", exact=True
                )
            ).to_have_attribute(
                "href", "/wiki/disciplines/programming-workshop-bachelors-5sem"
            )
            assert admin.locator("a[href^='http']").count() == 0
            admin.screenshot(
                path="/tmp/miniwiki-profile2-home-desktop.png", full_page=True
            )
            for width in (390, 320):
                admin.set_viewport_size({"width": width, "height": 844})
                assert admin.evaluate("document.documentElement.scrollWidth") <= width
                admin.screenshot(
                    path=f"/tmp/miniwiki-profile2-home-{width}.png", full_page=True
                )
            admin.set_viewport_size({"width": 1440, "height": 1000})
            guest_course = admin.goto(f"{BASE_URL}/wiki/disciplines/nlp")
            assert guest_course is not None and guest_course.status == 200
            expect(admin).to_have_url(f"{BASE_URL}/login")
            expect(admin).to_have_url(f"{BASE_URL}/login")
            no_script.goto(f"{BASE_URL}/login")
            no_script.get_by_label("Имя пользователя").fill(ADMIN_USERNAME)
            secret_without_script = "No-script-secret-password"
            no_script.get_by_label("Пароль").fill(secret_without_script)
            with no_script.expect_navigation() as navigation:
                no_script.get_by_role("button", name="Войти").click()
            response = navigation.value
            assert response is not None and response.status in (403, 422)
            submitted = response.request
            assert submitted.method == "POST"
            assert secret_without_script not in submitted.url
            no_script.close()
            response = admin.goto(f"{BASE_URL}/pages")
            assert response is not None and response.status == 200
            expect(admin).to_have_url(f"{BASE_URL}/login")
            expect(admin.get_by_role("heading", name="Вход")).to_be_visible()
            admin.screenshot(path="/tmp/miniwiki-06-login-desktop.png", full_page=True)

            admin.get_by_label("Имя пользователя").fill(ADMIN_USERNAME)
            admin.get_by_label("Пароль").fill("deliberately-wrong-password")
            admin.get_by_role("button", name="Войти").click()
            expect(admin.get_by_role("alert")).to_contain_text(
                "Неверное имя пользователя или пароль"
            )
            admin.get_by_label("Пароль").fill(ADMIN_PASSWORD)
            admin.get_by_role("button", name="Войти").click()
            expect(admin).to_have_url(f"{BASE_URL}/")
            expect(
                admin.get_by_role("heading", name="Учебные дисциплины")
            ).to_be_visible()
            expect(admin.locator(".create-page-link")).to_have_attribute(
                "href", "/pages/new"
            )
            expect(admin.get_by_text("Browser Administrator · admin")).to_be_visible()
            admin.goto(f"{BASE_URL}/users")
            expect(admin.get_by_role("heading", name="Пользователи")).to_be_visible()
            expect(admin.locator("[data-create-user]")).to_have_attribute(
                "method", "post"
            )
            expect(admin.locator("[data-create-user]")).to_have_attribute(
                "action", "/api/users"
            )
            own_row = admin.locator("[data-user-row]").filter(has_text=ADMIN_USERNAME)
            own_row.locator("[name='first_name']").fill("Browser Verified")
            with admin.expect_navigation():
                own_row.get_by_role("button", name="Сохранить").click()
            expect(
                admin.get_by_text("Browser Verified Administrator · admin")
            ).to_be_visible()
            assert (
                admin.evaluate(
                    "fetch('/api/auth/me').then(response => response.status)"
                )
                == 200
            )

            for username, role in ((editor_name, "editor"), (reader_name, "reader")):
                admin.get_by_label("Имя пользователя").fill(username)
                admin.get_by_label("Имя", exact=True).first.fill("Demo")
                admin.get_by_label("Фамилия", exact=True).first.fill(role.title())
                admin.get_by_label("Начальный пароль").fill(initial_password)
                admin.locator("#new-role").select_option(role)
                admin.get_by_role("button", name="Создать пользователя").click()
                expect(
                    admin.locator("[data-user-row]").filter(has_text=username)
                ).to_be_visible()
            expect(admin.locator("body")).not_to_contain_text(initial_password)
            admin.evaluate("window.scrollTo(0, 0)")
            admin.wait_for_function("window.scrollY === 0")
            admin.screenshot(
                path="/tmp/miniwiki-06-users-admin-desktop.png", full_page=True
            )
            for width in (390, 320):
                admin.set_viewport_size({"width": width, "height": 844})
                admin.evaluate("window.scrollTo(0, 0)")
                admin.wait_for_function("window.scrollY === 0")
                assert admin.evaluate("document.documentElement.scrollWidth") <= width
                admin.screenshot(
                    path=f"/tmp/miniwiki-06-users-admin-{width}.png", full_page=True
                )
            admin.set_viewport_size({"width": 1440, "height": 1000})

            admin.goto(f"{BASE_URL}/pages")
            tree = admin.get_by_role("navigation", name="Дерево страниц")
            degree_toggle = tree.get_by_role(
                "button", name="Развернуть раздел Бакалавриат"
            )
            expect(degree_toggle).to_be_visible()
            degree_toggle.click()
            year_toggle = tree.get_by_role("button", name="Развернуть раздел 3 курс")
            expect(year_toggle).to_be_visible()
            year_toggle.click()
            discipline = "Обработка естественного языка"
            discipline_toggle = tree.get_by_role(
                "button", name=f"Развернуть раздел {discipline}", exact=True
            )
            expect(discipline_toggle).to_be_visible()
            expect(tree.get_by_role("link", name="Основная страница")).to_have_count(0)
            discipline_toggle.click()
            expect(
                tree.get_by_role(
                    "button", name=f"Свернуть раздел {discipline}", exact=True
                )
            ).to_have_attribute("aria-expanded", "true")
            expect(
                tree.get_by_role("link", name="Основная страница")
            ).to_have_attribute("href", "/wiki/disciplines/nlp")
            lecture_toggle = tree.get_by_role("button", name="Развернуть раздел Лекции")
            expect(lecture_toggle).to_be_visible()
            lecture_toggle.click()
            expect(
                tree.get_by_role(
                    "link", name="Предварительная обработка текстовых данных (2025)"
                )
            ).to_be_visible()
            discipline_toggle = tree.get_by_role(
                "button", name=f"Свернуть раздел {discipline}", exact=True
            )
            discipline_toggle.focus()
            discipline_toggle.press("Space")
            expect(
                tree.get_by_role(
                    "button", name=f"Развернуть раздел {discipline}", exact=True
                )
            ).to_have_attribute("aria-expanded", "false")
            expect(
                tree.get_by_role(
                    "link", name="Предварительная обработка текстовых данных (2025)"
                )
            ).to_have_count(0)
            assert page_errors == []
            admin.screenshot(
                path="/tmp/miniwiki-profile2-tree-collapsed.png", full_page=True
            )

            admin.goto(f"{BASE_URL}/wiki/disciplines/nlp")
            expect(admin.locator("#page-title")).to_have_text(
                "Обработка естественного языка"
            )
            expect(admin.locator(".last-editor-name")).to_have_text("Не указан")
            admin.locator("[data-page-article]").get_by_role(
                "link", name="Предварительная обработка текстовых данных"
            ).click()
            expect(admin).to_have_url(
                f"{BASE_URL}/wiki/disciplines/nlp/lectures/preprocessing"
            )
            expect(admin.locator("#page-title")).to_have_text(
                "Предварительная обработка текстовых данных (2025)"
            )
            article_box = admin.locator("[data-page-article]").bounding_box()
            assert article_box is not None and 950 <= article_box["width"] <= 1000
            sidebar_toggle = admin.locator("[data-sidebar-toggle]")
            sidebar_toggle.focus()
            sidebar_toggle.press("Enter")
            expect(admin.locator("body")).to_have_class(
                re.compile(r"\bsidebar-collapsed\b")
            )
            expect(admin.locator("#wiki-sidebar")).to_be_hidden()
            collapsed_article = admin.locator("[data-page-article]").bounding_box()
            collapsed_toc = admin.locator(".toc-card").bounding_box()
            collapsed_grid = admin.locator(".content-grid").bounding_box()
            assert collapsed_article is not None
            assert collapsed_toc is not None and 200 <= collapsed_toc["width"] <= 220
            assert collapsed_grid is not None and collapsed_grid["width"] <= 1400
            assert 1000 <= collapsed_article["width"] <= 1150
            admin.set_viewport_size({"width": 1920, "height": 1280})
            wide_article = admin.locator("[data-page-article]").bounding_box()
            wide_grid = admin.locator(".content-grid").bounding_box()
            assert wide_article is not None and wide_article["width"] <= 1150
            assert wide_grid is not None and wide_grid["width"] <= 1400
            admin.set_viewport_size({"width": 1440, "height": 1000})
            sidebar_toggle.focus()
            sidebar_toggle.press("Space")
            expect(admin.locator("body")).not_to_have_class(
                re.compile(r"\bsidebar-collapsed\b")
            )
            expect(admin.locator("#wiki-sidebar")).to_be_visible()
            tree = admin.get_by_role("navigation", name="Дерево страниц")
            expect(
                tree.get_by_role(
                    "link", name="Предварительная обработка текстовых данных (2025)"
                )
            ).to_have_attribute("aria-current", "page")
            assert tree.locator("[data-tree-toggle][aria-expanded='true']").count() >= 2
            expect(tree.get_by_text("Очистка", exact=True)).to_have_count(0)
            expect(
                admin.get_by_role("navigation", name="Оглавление статьи").get_by_role(
                    "link", name="Очистка", exact=True
                )
            ).to_be_visible()
            expect(admin.locator(".breadcrumbs")).to_have_count(0)
            regex_table = admin.locator("[data-page-article] table").first
            expect(regex_table.locator("tbody tr")).to_have_count(21)
            assert (
                admin.locator("[data-page-article]").evaluate(
                    "element => element.textContent.split('</w>').length - 1"
                )
                == 13
            )
            expect(
                admin.locator(
                    "[data-page-article] a[href='/wiki/disciplines/nlp']"
                ).first
            ).to_be_visible()
            admin.goto(f"{BASE_URL}/wiki/disciplines/nlp/lectures/preprocessing")
            admin.screenshot(
                path="/tmp/miniwiki-profile2-preprocessing-desktop.png", full_page=True
            )
            admin.get_by_role(
                "heading", name="Основные элементы регулярных выражений"
            ).scroll_into_view_if_needed()
            admin.screenshot(
                path="/tmp/miniwiki-profile2-preprocessing-regex.png",
                full_page=False,
            )
            admin.get_by_role(
                "heading", name="Subword-токенизация"
            ).scroll_into_view_if_needed()
            admin.screenshot(
                path="/tmp/miniwiki-profile2-preprocessing-bpe.png", full_page=False
            )
            lecture_folder = tree.locator(
                "[data-tree-toggle][data-tree-title='Лекции']"
            ).first
            lecture_folder.click()
            expect(
                tree.get_by_role(
                    "link", name="Предварительная обработка текстовых данных (2025)"
                )
            ).to_have_count(0)
            lecture_folder.click()
            expect(
                tree.get_by_role(
                    "link", name="Предварительная обработка текстовых данных (2025)"
                )
            ).to_be_visible()
            for width in (390, 320):
                admin.set_viewport_size({"width": width, "height": 844})
                admin.evaluate("window.scrollTo(0, 0)")
                admin.wait_for_function("window.scrollY === 0")
                assert admin.evaluate("document.documentElement.scrollWidth") <= width
                admin.screenshot(
                    path=f"/tmp/miniwiki-profile2-preprocessing-{width}.png",
                    full_page=False,
                )
            admin.set_viewport_size({"width": 1440, "height": 1000})
            admin.goto(
                f"{BASE_URL}/wiki/disciplines/programming-workshop-bachelors-5sem"
            )
            expect(admin).to_have_url(
                f"{BASE_URL}/wiki/disciplines/programming-workshop-bachelors-5sem"
            )
            practice = admin.locator("[data-page-article]")
            expect(practice.locator("table").first.locator("tbody tr")).to_have_count(
                13
            )
            expect(
                practice.get_by_role(
                    "link",
                    name="Лекция 1. Методология CRISP-DM. Начало работы над ML-проектом",
                )
            ).to_have_attribute(
                "href",
                "https://docs.google.com/presentation/d/1tKrjcpheXF5vQyi5oCrYbrh4LJ5tuCstLkMo1bchjN0/edit?usp=sharing",
            )
            external_links = practice.locator("a[href^='http']")
            expect(external_links).to_have_count(1)
            admin.screenshot(
                path="/tmp/miniwiki-profile2-practice-desktop.png", full_page=True
            )
            admin.set_viewport_size({"width": 1000, "height": 1000})
            open_practice_toc = admin.locator(".toc-card").bounding_box()
            assert open_practice_toc is not None and open_practice_toc["width"] == 220
            admin.locator("[data-sidebar-toggle]").click()
            collapsed_practice_toc = admin.locator(".toc-card").bounding_box()
            assert collapsed_practice_toc is not None
            assert collapsed_practice_toc["width"] == 220
            admin.set_viewport_size({"width": 1440, "height": 1000})
            admin.locator("[data-sidebar-toggle]").click()

            admin.goto(f"{BASE_URL}/users")
            expect(admin.locator("body")).not_to_contain_text("· вы")
            expect(admin.locator("body")).not_to_contain_text(re.compile(r"\bID\s+\d+"))

            _create_page(admin, private_path, secret_title)
            _create_page(admin, public_path, f"Public article {run}", "public")
            _create_page(admin, child_path, child_title, "public, child-check")

            editor = browser.new_page(viewport={"width": 1440, "height": 1000})
            sign_in(editor, editor_name, initial_password)
            expect(editor.get_by_text("Demo Editor · editor")).to_be_visible()
            expect(editor.locator(".create-page-link")).to_have_attribute(
                "href", "/pages/new"
            )
            editor.goto(f"{BASE_URL}/wiki{private_path}")
            expect(editor.locator("#page-title")).to_have_text(secret_title)
            editor.goto(f"{BASE_URL}/pages/new")
            editor.get_by_label("Иерархический путь").fill(f"/editor-created-{run}")
            editor.get_by_label("Заголовок").fill(f"Editor article {run}")
            editor.get_by_label("Теги").fill("")
            editor.get_by_label("Текст страницы (Markdown)").fill(
                "## Editor preview\n\nSafe."
            )
            editor.get_by_role("button", name="Обновить предпросмотр").click()
            expect(
                editor.locator("[data-preview-content]").get_by_role(
                    "heading", name="Editor preview"
                )
            ).to_be_visible()
            with editor.expect_navigation():
                editor.get_by_role("button", name="Создать страницу").click()
            expect(editor.locator("#page-title")).to_have_text(f"Editor article {run}")
            expect(editor.locator(".creator-attribution")).to_have_count(0)
            expect(editor.locator(".last-editor-name")).to_have_text("Demo Editor")
            expect(editor.locator(".last-change-card time")).to_contain_text("(Омск)")
            editor.screenshot(path="/tmp/miniwiki-06-role-editor.png", full_page=True)
            forbidden_users = editor.goto(f"{BASE_URL}/users")
            assert forbidden_users is not None and forbidden_users.status == 403
            editor.goto(f"{BASE_URL}/pages")
            editor.get_by_role("button", name="Выйти").click()
            expect(editor).to_have_url(f"{BASE_URL}/login")
            assert (
                editor.evaluate(
                    "fetch('/api/auth/me').then(response => response.status)"
                )
                == 401
            )

            reader = browser.new_page(viewport={"width": 1440, "height": 1000})
            sign_in(reader, reader_name, initial_password)
            expect(reader.get_by_text("Demo Reader · reader")).to_be_visible()
            expect(reader.locator(".create-page-link")).to_have_count(0)
            reader.goto(f"{BASE_URL}/pages")
            expect(
                reader.locator(".page-item-title", has_text=child_title)
            ).to_be_visible()
            expect(
                reader.locator(".page-item-title", has_text=secret_title)
            ).to_have_count(0)
            expect(
                reader.locator(".page-item-title", has_text=f"Public article {run}")
            ).to_be_visible()
            reader.get_by_label("Поиск по заголовку и тексту").fill(secret_title)
            reader.get_by_role("button", name="Найти").click()
            expect(
                reader.get_by_role("heading", name="Ничего не найдено")
            ).to_be_visible()
            reader.goto(f"{BASE_URL}/pages")
            reader.locator("select[name='tag']").select_option("public")
            reader.get_by_role("button", name="Найти").click()
            expect(
                reader.locator(".page-item-title", has_text=child_title)
            ).to_be_visible()
            assert (
                reader.locator(".page-item-title", has_text=secret_title).count() == 0
            )
            tree = reader.get_by_role("navigation", name="Дерево страниц")
            expect(tree.get_by_text(secret_title)).to_have_count(0)
            reader.screenshot(
                path="/tmp/miniwiki-06-role-reader-desktop.png", full_page=True
            )
            forbidden_new = reader.goto(f"{BASE_URL}/pages/new")
            assert forbidden_new is not None and forbidden_new.status == 403
            hidden_article = reader.goto(f"{BASE_URL}/wiki{private_path}")
            assert hidden_article is not None and hidden_article.status == 404
            visible_child = reader.goto(f"{BASE_URL}/wiki{child_path}")
            assert visible_child is not None and visible_child.status == 200
            expect(reader.locator("#page-title")).to_have_text(child_title)
            tree = reader.get_by_role("navigation", name="Дерево страниц")
            expect(tree.get_by_role("link", name=child_title)).to_be_visible()
            expect(tree.get_by_text(secret_title)).to_have_count(0)
            for width in (390, 320):
                reader.set_viewport_size({"width": width, "height": 844})
                reader.evaluate("window.scrollTo(0, 0)")
                reader.wait_for_function("window.scrollY === 0")
                assert reader.evaluate("document.documentElement.scrollWidth") <= width
                reader.screenshot(
                    path=f"/tmp/miniwiki-06-role-reader-{width}.png", full_page=False
                )

            admin.goto(f"{BASE_URL}/users")
            reader_id = (
                admin.locator("[data-user-row]")
                .filter(has_text=reader_name)
                .get_attribute("data-user-id")
            )
            assert reader_id is not None
            status_code = admin.evaluate(
                """async ({ id, password }) => {
                  const tokenResponse = await fetch('/api/auth/csrf');
                  const { csrf_token } = await tokenResponse.json();
                  const response = await fetch(`/api/users/${id}`, {
                    method: 'PATCH',
                    headers: { 'Content-Type': 'application/json', 'X-CSRF-Token': csrf_token },
                    body: JSON.stringify({ password })
                  });
                  return response.status;
                }""",
                {"id": reader_id, "password": reset_password},
            )
            assert status_code == 200
            assert (
                reader.evaluate(
                    "fetch('/api/auth/me').then(response => response.status)"
                )
                == 401
            )
            reader.reload()
            expect(reader).to_have_url(f"{BASE_URL}/login")
        finally:
            browser.close()
