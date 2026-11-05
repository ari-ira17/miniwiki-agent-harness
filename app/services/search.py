"""Case-insensitive page search shared by API and HTML list views."""

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.models.page import Page
from app.models.tag import Tag
from app.services.permissions import all_pages_scope
from app.services.tags import normalize_tag


def search_pages(
    session: Session,
    *,
    query: str = "",
    tag: str | None = None,
    limit: int = 50,
    offset: int = 0,
    scope=all_pages_scope,
) -> tuple[list[Page], int]:
    """Search title/body and optional tag, applying access before count/page."""
    statement = select(Page).where(scope())
    if query:
        needle = query.lower()
        statement = statement.where(
            or_(
                func.lower(Page.title).contains(needle, autoescape=True),
                func.lower(Page.markdown).contains(needle, autoescape=True),
            )
        )
    if tag:
        statement = statement.where(Page.tags.any(Tag.name == normalize_tag(tag)))
    total = session.scalar(select(func.count()).select_from(statement.subquery())) or 0
    pages = list(
        session.scalars(
            statement.options(
                selectinload(Page.tags),
                joinedload(Page.author),
                joinedload(Page.last_editor),
            )
            .order_by(Page.path)
            .limit(limit)
            .offset(offset)
        )
    )
    return pages, total
