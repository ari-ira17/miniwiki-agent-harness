"""HTML views for page search, editing and hierarchical article navigation."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from sqlalchemy.orm import Session

from app.api.pages import get_page_scope
from app.db import get_session
from app.models.page import Page
from app.schemas.pages import PageLimit, validate_page_path
from app.services.markdown import render_document
from app.services.navigation import breadcrumbs, page_tree, visible_tags
from app.services.pages import PageNotFound, get_page, get_page_by_path
from app.services.permissions import PageScope
from app.services.search import search_pages
from app.services.tags import normalize_tag

router = APIRouter(include_in_schema=False)
APP_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=APP_DIR / "templates")
SessionDependency = Annotated[Session, Depends(get_session)]
ScopeDependency = Annotated[PageScope, Depends(get_page_scope)]


def _flatten_tree(nodes: list[dict], current_path: str | None = None) -> list[dict]:
    flattened: list[dict] = []

    def visit(items: list[dict], depth: int) -> None:
        for node in items:
            flattened.append(
                {**node, "depth": depth, "current": node["path"] == current_path}
            )
            visit(node["children"], depth + 1)

    visit(nodes, 0)
    return flattened


def _navigation_context(
    session: Session, scope: PageScope, current_path: str | None = None
) -> dict:
    return {
        "navigation_nodes": _flatten_tree(
            page_tree(session, scope=scope), current_path
        ),
        "visible_tags": visible_tags(session, scope=scope),
    }


@router.get("/pages", response_class=HTMLResponse)
def pages_index(
    request: Request,
    session: SessionDependency,
    scope: ScopeDependency,
    limit: PageLimit = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    q: Annotated[str, Query(max_length=200)] = "",
    tag: Annotated[str | None, Query(max_length=32)] = None,
):
    try:
        canonical_tag = normalize_tag(tag) if tag else None
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    pages, total = search_pages(
        session, query=q, tag=canonical_tag, limit=limit, offset=offset, scope=scope
    )
    return templates.TemplateResponse(
        request=request,
        name="pages/index.html",
        context={
            "pages": pages,
            "total": total,
            "limit": limit,
            "offset": offset,
            "q": q,
            "tag": canonical_tag,
            "previous_offset": max(0, offset - limit),
            "next_offset": offset + limit,
            "has_previous": offset > 0,
            "has_next": offset + limit < total,
            **_navigation_context(session, scope),
        },
    )


@router.get("/pages/new", response_class=HTMLResponse)
def new_page(request: Request, session: SessionDependency, scope: ScopeDependency):
    return templates.TemplateResponse(
        request=request,
        name="pages/editor.html",
        context={"page": None, "mode": "create", **_navigation_context(session, scope)},
    )


@router.get("/pages/{page_id}/edit", response_class=HTMLResponse)
def edit_page(
    request: Request, page_id: int, session: SessionDependency, scope: ScopeDependency
):
    try:
        page = get_page(session, page_id, scope=scope)
    except PageNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    return templates.TemplateResponse(
        request=request,
        name="pages/editor.html",
        context={"page": page, "mode": "edit", **_navigation_context(session, scope)},
    )


@router.get("/pages/{page_id}", response_class=HTMLResponse)
def page_by_id(
    request: Request, page_id: int, session: SessionDependency, scope: ScopeDependency
):
    try:
        page = get_page(session, page_id, scope=scope)
    except PageNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    return _render_article(request, page, session, scope)


@router.get("/wiki/{page_path:path}", response_class=HTMLResponse)
def page_by_path(
    request: Request, page_path: str, session: SessionDependency, scope: ScopeDependency
):
    try:
        path = validate_page_path(f"/{page_path}")
        page = get_page_by_path(session, path, scope=scope)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    except PageNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    return _render_article(request, page, session, scope)


def _render_article(
    request: Request, page: Page, session: Session, scope: PageScope
) -> HTMLResponse:
    sanitized_html, outline = render_document(page.markdown)
    return templates.TemplateResponse(
        request=request,
        name="pages/article.html",
        context={
            "page": page,
            "rendered_html": Markup(sanitized_html),
            "outline": outline,
            "breadcrumbs": breadcrumbs(session, page.path, scope=scope),
            **_navigation_context(session, scope, page.path),
        },
    )
