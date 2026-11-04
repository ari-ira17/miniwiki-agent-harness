"""Browser coverage for search, tags and hierarchical article navigation."""

import os

import pytest
from playwright.sync_api import Page, expect, sync_playwright

pytestmark = pytest.mark.e2e
BASE_URL = os.environ.get("MINIWIKI_E2E_URL", "http://127.0.0.1:8000")


def test_search_tags_tree_toc_and_responsive_layout() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page: Page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.goto(f"{BASE_URL}/pages")
        expect(page.get_by_role("heading", name="Страницы", exact=True)).to_be_visible()
        page.evaluate("() => document.fonts.ready.then(() => true)")
        assert page.evaluate("document.fonts.check('16px Roboto')")
        assert (
            page.locator(".sidebar").evaluate(
                "el => getComputedStyle(el).backgroundColor"
            )
            == "rgb(98, 33, 40)"
        )
        page.screenshot(path="/tmp/miniwiki-navigation-search.png", full_page=True)

        page.locator(".search-controls select[name='tag']").select_option("демо")
        page.get_by_role("button", name="Найти").click()
        expect(page.locator(".page-item")).to_have_count(4)
        expect(page.locator(".page-item .tag-chip", has_text="#демо")).to_have_count(4)
        page.screenshot(path="/tmp/miniwiki-navigation-tag-filter.png", full_page=True)

        page.get_by_label("Поиск по заголовку и тексту").fill("лингвистика")
        page.locator(".search-controls select[name='tag']").select_option("")
        page.get_by_role("button", name="Найти").click()
        expect(page.locator(".page-item-title", has_text="Лингвистика")).to_be_visible()
        page.get_by_label("Поиск по заголовку и тексту").fill("запрос-которого-нет")
        page.get_by_role("button", name="Найти").click()
        expect(page.get_by_role("heading", name="Ничего не найдено")).to_be_visible()
        page.screenshot(path="/tmp/miniwiki-navigation-empty.png", full_page=True)

        page.goto(f"{BASE_URL}/wiki/demo/linguistics/search")
        expect(
            page.get_by_role("navigation", name="Дерево страниц").get_by_role(
                "link", name="Поиск по корпусу"
            )
        ).to_have_attribute("aria-current", "page")
        expect(
            page.get_by_role("navigation", name="Навигационная цепочка")
        ).to_be_visible()
        expect(
            page.get_by_role("navigation", name="Оглавление статьи").get_by_role(
                "link", name="Подготовка корпуса"
            )
        ).to_be_visible()
        expect(page.locator(".heading-tags .tag-chip")).to_have_count(2)
        page.screenshot(path="/tmp/miniwiki-navigation-article.png", full_page=True)
        page.get_by_role("link", name="#поиск").click()
        expect(page.locator(".page-item")).to_have_count(1)
        expect(
            page.locator(".page-item-title", has_text="Поиск по корпусу")
        ).to_be_visible()
        page.goto(f"{BASE_URL}/wiki/demo/linguistics/search")
        page.get_by_role("link", name="Редактировать").click()
        page.get_by_label("Теги").fill("браузер, DEMO")
        with page.expect_navigation():
            page.get_by_role("button", name="Сохранить изменения").click()
        expect(page.locator(".heading-tags .tag-chip")).to_have_count(2)
        expect(
            page.locator(".heading-tags .tag-chip", has_text="#браузер")
        ).to_be_visible()

        page.goto(f"{BASE_URL}/wiki/demo/long-article")
        toc = page.get_by_role("navigation", name="Оглавление статьи")
        assert toc.evaluate("el => el.scrollHeight > el.clientHeight")
        page.evaluate("window.scrollTo({ top: 900, behavior: 'instant' })")
        page.wait_for_function(
            "document.querySelector('.article-toc').getBoundingClientRect().top >= 64"
        )
        subheading = toc.locator("a.toc-level-4").first
        subheading.click()
        page.wait_for_function(
            "() => location.hash && document.getElementById(decodeURIComponent(location.hash.slice(1)))?.getBoundingClientRect().top >= 64"
        )

        for width in (390, 320):
            page.set_viewport_size({"width": width, "height": 844})
            assert page.evaluate("document.documentElement.scrollWidth") <= width
        page.screenshot(path="/tmp/miniwiki-navigation-mobile.png", full_page=False)
        browser.close()
