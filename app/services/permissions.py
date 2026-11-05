"""Shared SQL visibility scopes applied to every page read channel."""

from collections.abc import Callable

from sqlalchemy import true
from sqlalchemy.sql.elements import ColumnElement

from app.models.page import Page
from app.models.tag import Tag

PageScope = Callable[[], ColumnElement[bool]]


def all_pages_scope() -> ColumnElement[bool]:
    """Return all pages for administrators and editors."""
    return true()


def public_pages_scope() -> ColumnElement[bool]:
    """Readers can see only pages that carry the canonical public tag."""
    return Page.tags.any(Tag.name == "public")
