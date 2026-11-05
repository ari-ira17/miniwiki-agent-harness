"""Reusable browser login for isolated Compose E2E runs."""

import os

from playwright.sync_api import Page, expect

BASE_URL = os.environ.get("MINIWIKI_E2E_URL", "http://127.0.0.1:8000")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "")


def sign_in(
    page: Page, username: str = ADMIN_USERNAME, password: str = ADMIN_PASSWORD
) -> None:
    if not password:
        raise RuntimeError(
            "The isolated E2E Compose profile must provide ADMIN_PASSWORD."
        )
    page.goto(f"{BASE_URL}/login")
    expect(page.get_by_role("heading", name="Вход")).to_be_visible()
    page.get_by_label("Имя пользователя").fill(username)
    page.get_by_label("Пароль").fill(password)
    page.get_by_role("button", name="Войти").click()
    expect(page).to_have_url(f"{BASE_URL}/")
    expect(page.get_by_role("heading", name="Учебные дисциплины")).to_be_visible()
