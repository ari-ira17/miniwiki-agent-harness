"""Browser workflow for Markdown preview and page CRUD."""

import os
import re
from uuid import uuid4

import pytest
from playwright.sync_api import Page, expect, sync_playwright

from tests.e2e.helpers import sign_in

pytestmark = pytest.mark.e2e
BASE_URL = os.environ.get("MINIWIKI_E2E_URL", "http://127.0.0.1:8000")


def test_create_preview_edit_read_and_delete_page() -> None:
    slug = f"browser-{uuid4().hex[:10]}"
    path = f"/e2e/{slug}"
    dialogs: list[str] = []

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page: Page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("dialog", lambda dialog: (dialogs.append(dialog.type), dialog.accept()))
        sign_in(page)
        page.goto(f"{BASE_URL}/pages/new")

        expect(page.get_by_role("heading", name="РЕДАКТОР MARKDOWN")).to_be_visible()
        expect(page.locator(".editor-backlink")).to_have_attribute("href", "/pages")
        expect(page.locator(".toc-card")).to_have_count(0)
        assert (
            len(
                page.locator(".content-grid")
                .evaluate("element => getComputedStyle(element).gridTemplateColumns")
                .split()
            )
            == 1
        )
        textarea = page.get_by_label("Текст страницы (Markdown)")
        assert (
            textarea.evaluate("element => element.getBoundingClientRect().width") > 500
        )
        assert (
            textarea.evaluate("element => getComputedStyle(element).minHeight")
            == "280px"
        )
        assert (
            page.get_by_role("button", name="Создать страницу").evaluate(
                "element => getComputedStyle(element).backgroundColor"
            )
            == "rgb(98, 33, 40)"
        )
        page.get_by_label("Иерархический путь").fill(path)
        page.get_by_label("Заголовок").fill("Небольшая статья")
        page.get_by_label("Текст страницы (Markdown)").fill(
            "## Предпросмотр\n\n- первый пункт\n- второй пункт\n\n"
            "<script>alert(1)</script>"
        )
        page.get_by_role("button", name="Обновить предпросмотр").click()

        preview = page.locator("[data-preview-content]")
        expect(preview.get_by_role("heading", name="Предпросмотр")).to_be_visible()
        expect(preview.locator("li")).to_have_count(2)
        expect(preview.locator("script")).to_have_count(0)
        expect(page.get_by_role("alert")).to_have_count(0)
        page.evaluate("window.scrollTo({ top: 0, behavior: 'instant' })")
        page.screenshot(path="/tmp/miniwiki-06-editor-preview.png", full_page=True)

        with page.expect_navigation():
            page.get_by_role("button", name="Создать страницу").click()
        expect(page).to_have_url(re.compile(rf"/wiki{re.escape(path)}$"))
        article = page.locator("[data-page-article]")
        expect(article.get_by_role("heading", name="Предпросмотр")).to_be_visible()
        expect(article.locator("script")).to_have_count(0)
        assert "alert(1)" not in article.inner_text()
        assert dialogs == []
        page.screenshot(path="/tmp/miniwiki-06-editor-article.png", full_page=True)

        article_id = article.get_attribute("data-page-id")
        page.get_by_role("link", name="Редактировать").click()
        expect(page.get_by_label("Иерархический путь")).to_have_attribute(
            "readonly", ""
        )
        page.get_by_label("Заголовок").fill("Обновлённая статья")
        page.get_by_label("Текст страницы (Markdown)").fill(
            "# Сохранённая версия\n\nГотово."
        )
        with page.expect_navigation():
            page.get_by_role("button", name="Сохранить изменения").click()
        expect(
            page.locator("[data-page-article]").get_by_role(
                "heading", name="Сохранённая версия"
            )
        ).to_be_visible()

        page.goto(f"{BASE_URL}/pages/{article_id}/edit")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth") <= page.evaluate(
            "window.innerWidth"
        )
        page.screenshot(path="/tmp/miniwiki-06-editor-mobile.png", full_page=True)
        with page.expect_navigation():
            page.get_by_role("button", name="Удалить").click()
        expect(page).to_have_url(f"{BASE_URL}/pages")
        expect(page.get_by_text("Обновлённая статья")).to_have_count(0)
        browser.close()
