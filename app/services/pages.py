"""Page operations shared by API and server-rendered interfaces."""

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.models.page import Page, utc_now
from app.schemas.pages import PageCreate, PageUpdate
from app.services.permissions import all_pages_scope
from app.services.tags import get_or_create_tags


class PageNotFound(Exception):
    """Raised when a requested page does not exist."""


class PagePathConflict(Exception):
    """Raised when a page path is already in use."""


class EmptyPageUpdate(Exception):
    """Raised when a patch contains no changes."""


def create_page(session: Session, data: PageCreate) -> Page:
    """Create a page, translating database uniqueness races into a domain error."""
    if session.scalar(select(Page.id).where(Page.path == data.path)) is not None:
        raise PagePathConflict
    values = data.model_dump(exclude={"tags"})
    page = Page(**values)
    page.tags = get_or_create_tags(session, data.tags)
    session.add(page)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        original = error.orig
        diagnostic = getattr(original, "diag", None)
        if (
            getattr(original, "sqlstate", None) == "23505"
            and getattr(diagnostic, "constraint_name", None) == "ix_pages_path"
        ):
            raise PagePathConflict from error
        raise
    session.refresh(page)
    return page


def list_pages(
    session: Session, limit: int, offset: int, *, scope=all_pages_scope
) -> tuple[list[Page], int]:
    """Return pages ordered by path with a total count."""
    pages = list(
        session.scalars(
            select(Page)
            .where(scope())
            .options(selectinload(Page.tags))
            .order_by(Page.path)
            .limit(limit)
            .offset(offset)
        )
    )
    total = session.scalar(select(func.count()).select_from(Page).where(scope())) or 0
    return pages, total


def get_page(session: Session, page_id: int, *, scope=all_pages_scope) -> Page:
    """Return a page by id or raise a domain error."""
    page = session.scalar(
        select(Page).where(Page.id == page_id, scope()).options(selectinload(Page.tags))
    )
    if page is None:
        raise PageNotFound
    return page


def get_page_by_path(session: Session, path: str, *, scope=all_pages_scope) -> Page:
    """Return a page by canonical path or raise a domain error."""
    page = session.scalar(
        select(Page).where(Page.path == path, scope()).options(selectinload(Page.tags))
    )
    if page is None:
        raise PageNotFound
    return page


def update_page(
    session: Session, page_id: int, data: PageUpdate, *, scope=all_pages_scope
) -> Page:
    """Update editable fields, preserving the immutable path."""
    page = get_page(session, page_id, scope=scope)
    changes = data.model_dump(exclude_unset=True)
    if not changes:
        raise EmptyPageUpdate
    tags = changes.pop("tags", None)
    for field, value in changes.items():
        setattr(page, field, value)
    if tags is not None:
        current_tags = {tag.name for tag in page.tags}
        if current_tags != set(tags):
            page.tags = get_or_create_tags(session, tags)
            page.updated_at = utc_now()
    session.commit()
    session.refresh(page)
    return page


def delete_page(session: Session, page_id: int) -> None:
    """Delete only the selected article; descendants are independent records."""
    page = get_page(session, page_id)
    session.delete(page)
    session.commit()
