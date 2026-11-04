"""Shared page visibility scope for every read channel.

Stage 6 will derive this SQL predicate from the authenticated principal. Keeping
the scope injectable now ensures each consumer applies it before counts/joins.
"""

from collections.abc import Callable

from sqlalchemy import true
from sqlalchemy.sql.elements import ColumnElement

from app.models.page import Page

PageScope = Callable[[], ColumnElement[bool]]


def all_pages_scope() -> ColumnElement[bool]:
    """Return the local-prototype scope; authentication is not implemented yet."""
    return true()


def public_pages_scope() -> ColumnElement[bool]:
    """Return the future reader scope, exposed for policy tests."""
    return Page.is_public.is_(True)
