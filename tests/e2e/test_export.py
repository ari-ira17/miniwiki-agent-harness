"""Browser download and role visibility for the wiki export."""

from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from tempfile import TemporaryDirectory
from threading import Thread
from uuid import uuid4
from zipfile import ZipFile

import pytest
from playwright.sync_api import Browser, expect, sync_playwright

from tests.e2e.helpers import BASE_URL, sign_in

pytestmark = pytest.mark.e2e


def _capture_archive_listing(browser: Browser, directory: str, parent: str) -> None:
    handler = partial(SimpleHTTPRequestHandler, directory=directory)
    with ThreadingHTTPServer(("127.0.0.1", 0), handler) as server:
        thread = Thread(target=server.serve_forever)
        thread.start()
        try:
            page = browser.new_page(viewport={"width": 1000, "height": 360})
            page.goto(f"http://127.0.0.1:{server.server_port}/{parent}/")
            expect(page.get_by_role("link", name="child.md")).to_be_visible()
            page.screenshot(path="/tmp/miniwiki-07-export-archive.png")
            page.close()
        finally:
            server.shutdown()
            thread.join()


def test_admin_downloads_archive_from_header() -> None:
    parent = f"export-{uuid4().hex[:8]}"
    markdown = "# Проверка\n\n**Исходный Markdown**"
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        try:
            admin = browser.new_page(viewport={"width": 1440, "height": 900})
            admin.goto(f"{BASE_URL}/login")
            expect(admin.get_by_role("link", name="Скачать ZIP")).to_have_count(0)
            assert admin.request.get(f"{BASE_URL}/api/export").status == 401
            sign_in(admin)

            csrf = admin.request.get(f"{BASE_URL}/api/auth/csrf").json()["csrf_token"]
            headers = {"X-CSRF-Token": csrf}
            for path, tags in ((parent, ["public"]), (f"{parent}/child", [])):
                response = admin.request.post(
                    f"{BASE_URL}/api/pages",
                    data={
                        "path": f"/{path}",
                        "title": "Проверка",
                        "markdown": markdown,
                        "tags": tags,
                    },
                    headers=headers,
                )
                assert response.status == 201, response.text()

            download_link = admin.get_by_role("link", name="Скачать ZIP")
            expect(download_link).to_be_visible()
            with admin.expect_download() as download_info:
                download_link.click()
            download = download_info.value
            assert download.suggested_filename == "miniwiki-export.zip"
            with TemporaryDirectory() as directory, ZipFile(download.path()) as archive:
                assert archive.testzip() is None
                print(
                    f"Downloaded {download.suggested_filename} with {len(archive.namelist())} pages"
                )
                for name in (f"{parent}.md", f"{parent}/child.md"):
                    body = archive.read(name).split(b"\n---\n", 1)[1]
                    assert body == markdown.encode("utf-8")
                    print(f"  {name}: stored Markdown verified byte for byte")
                    archive.extract(name, directory)
                _capture_archive_listing(browser, directory, parent)
            admin.screenshot(path="/tmp/miniwiki-07-export-download.png")

            for role in ("editor", "reader"):
                username = f"{parent}-{role}"
                password = "Browser-export-fixture-123"
                response = admin.request.post(
                    f"{BASE_URL}/api/users",
                    data={
                        "username": username,
                        "password": password,
                        "first_name": "Export",
                        "last_name": role.title(),
                        "role": role,
                    },
                    headers=headers,
                )
                assert response.status == 201, response.text()
                page = browser.new_page()
                sign_in(page, username, password)
                expect(page.get_by_role("link", name="Скачать ZIP")).to_have_count(0)
                for route in ("/export", "/api/export"):
                    assert page.request.get(f"{BASE_URL}{route}").status == 403
                page.close()

            admin.goto(f"{BASE_URL}/docs")
            operation = admin.locator(".opblock").filter(
                has=admin.locator('[data-path="/api/export"]')
            )
            expect(operation).to_be_visible()
            operation.locator(".opblock-summary-control").click()
            expect(operation.get_by_text("Responses", exact=True)).to_be_visible()
            operation.screenshot(path="/tmp/miniwiki-07-api-openapi.png")
        finally:
            browser.close()
