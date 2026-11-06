"""Browser coverage for search, tags and hierarchical article navigation."""

import os

import pytest
from playwright.sync_api import Page, expect, sync_playwright

from tests.e2e.helpers import sign_in

pytestmark = pytest.mark.e2e
BASE_URL = os.environ.get("MINIWIKI_E2E_URL", "http://127.0.0.1:8000")


def test_search_tags_tree_toc_and_responsive_layout() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        page: Page = browser.new_page(viewport={"width": 1440, "height": 1000})
        sign_in(page)
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
        ).to_have_count(0)
        expect(
            page.get_by_role("navigation", name="Оглавление статьи").get_by_role(
                "link", name="Подготовка корпуса"
            )
        ).to_be_visible()
        expect(page.locator(".heading-tags .tag-chip")).to_have_count(3)
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

        layouts = (
            ("/", "home"),
            ("/wiki/disciplines/programming-workshop-bachelors-5sem", "course"),
            ("/wiki/disciplines/nlp/lectures/preprocessing", "lecture"),
        )
        for path, capture in layouts:
            page.set_viewport_size({"width": 1440, "height": 900})
            page.goto(f"{BASE_URL}{path}")
            expect(page.locator(".page-heading h1")).to_be_visible()
            if path.startswith("/wiki/"):
                expect(
                    page.get_by_text(path.removeprefix("/wiki"), exact=True)
                ).to_have_count(0)
            toggle = page.locator("[data-sidebar-toggle]")
            alignment = """() => {
                const title = document.querySelector('.page-heading h1').getBoundingClientRect();
                const article = document.querySelector('.page-content > .article-card').getBoundingClientRect();
                return Math.abs(title.left - article.left) < 1;
            }"""
            for width in (1920, 1440, 1000, 390, 320):
                page.set_viewport_size({"width": width, "height": 900})
                for expanded in ("true", "false"):
                    if toggle.get_attribute("aria-expanded") != expanded:
                        toggle.click()
                    expect(toggle).to_have_attribute("aria-expanded", expanded)
                    page.wait_for_function(alignment)
                    button = toggle.bounding_box()
                    assert button is not None
                    assert button["x"] == (18 if width > 760 else 12)
                    toc = page.locator(".toc-card").bounding_box()
                    article = page.locator(
                        ".page-content > .article-card"
                    ).bounding_box()
                    assert toc is not None and article is not None
                    assert toc["width"] == (220 if width > 760 else article["width"])
                    assert (
                        page.evaluate("document.documentElement.scrollWidth") <= width
                    )
                    if width == 1440 and expanded == "true":
                        page.screenshot(
                            path=f"/tmp/miniwiki-heading-{capture}.png",
                            animations="disabled",
                        )
                    if width == 1440 and expanded == "false" and capture == "home":
                        page.screenshot(
                            path="/tmp/miniwiki-heading-home-collapsed.png",
                            animations="disabled",
                        )

        page.goto(f"{BASE_URL}/pages")
        expect(
            page.locator('.page-item[href*="programming-workshop-bachelors-5sem"]')
        ).to_be_visible()
        expect(
            page.get_by_text(
                "/disciplines/programming-workshop-bachelors-5sem", exact=True
            )
        ).to_have_count(0)
        browser.close()
