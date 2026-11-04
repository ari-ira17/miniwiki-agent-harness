"""Page tree, breadcrumbs and public tag listing under a shared visibility scope."""

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.page import Page
from app.services.permissions import all_pages_scope


def visible_pages(session: Session, *, scope=all_pages_scope) -> list[Page]:
    """Load only visible pages and their tags for navigation consumers."""
    return list(
        session.scalars(
            select(Page)
            .where(scope())
            .options(selectinload(Page.tags))
            .order_by(Page.path)
        )
    )


def page_tree(session: Session, *, scope=all_pages_scope) -> list[dict]:
    """Build virtual directory nodes from the filtered page set."""
    pages = visible_pages(session, scope=scope)
    nodes: dict[str, dict] = {}
    roots: list[dict] = []
    for page in pages:
        parts = page.path.strip("/").split("/")
        parent_path = ""
        for index, part in enumerate(parts):
            path = f"{parent_path}/{part}"
            node = nodes.get(path)
            if node is None:
                node = {"path": path, "title": part, "page_id": None, "children": []}
                nodes[path] = node
                (nodes[parent_path]["children"] if parent_path else roots).append(node)
            if index == len(parts) - 1:
                node["page_id"] = page.id
                node["title"] = page.title
            parent_path = path
    return roots


def breadcrumbs(session: Session, path: str, *, scope=all_pages_scope) -> list[dict]:
    """Return visible ancestors only; virtual ancestors have no article link."""
    pages = visible_pages(session, scope=scope)
    by_path = {page.path: page for page in pages}
    parts = path.strip("/").split("/")
    items = [{"title": "Страницы", "path": "/pages", "page_id": None}]
    current = ""
    for part in parts:
        current += f"/{part}"
        page = by_path.get(current)
        items.append(
            {
                "title": page.title if page else part,
                "path": current,
                "page_id": page.id if page else None,
            }
        )
    return items


def visible_tags(session: Session, *, scope=all_pages_scope) -> list[str]:
    """List only tags attached to pages in the current visibility scope."""
    pages = visible_pages(session, scope=scope)
    return sorted({tag.name for page in pages for tag in page.tags})
