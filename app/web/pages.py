"""HTML views for page search, editing and hierarchical article navigation."""

from pathlib import Path
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from markupsafe import Markup
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    get_html_page_scope,
    require_html_editor,
    require_html_user,
)
from app.db import get_session
from app.models.page import Page
from app.models.user import User
from app.schemas.pages import PageLimit, validate_page_path
from app.services.markdown import render_document
from app.services.navigation import page_tree, visible_pages, visible_tags
from app.services.pages import PageNotFound, get_page, get_page_by_path
from app.services.permissions import PageScope
from app.services.search import search_pages
from app.services.tags import normalize_tag

router = APIRouter(include_in_schema=False)
APP_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=APP_DIR / "templates")
SessionDependency = Annotated[Session, Depends(get_session)]
ScopeDependency = Annotated[PageScope, Depends(get_html_page_scope)]
HtmlUser = Annotated[User, Depends(require_html_user)]
HtmlEditor = Annotated[User, Depends(require_html_editor)]


def _decorate_tree(
    nodes: list[dict],
    current_path: str | None = None,
) -> list[dict]:
    decorated: list[dict] = []
    for node in nodes:
        path = node["path"]
        title = node["title"]
        if node["page_id"] is None:
            title = {"disciplines": "Дисциплины", "lectures": "Лекции"}.get(
                title, title
            )
        expanded = bool(
            current_path
            and (path == current_path or current_path.startswith(f"{path}/"))
        )
        children = _decorate_tree(node["children"], current_path)
        kind = "document" if node["page_id"] is not None else "folder"
        decorated.append(
            {
                **node,
                "kind": kind,
                "title": title,
                "current": path == current_path,
                "expanded": expanded,
                "tree_id": f"tree{path.replace('/', '_')}",
                "children": children,
            }
        )
    return decorated


COURSE_PAGES = (
    ("/disciplines/nlp", "bachelors", "3"),
    ("/disciplines/programming-workshop-bachelors-5sem", "bachelors", "3"),
)

DEGREE_GROUPS = (
    ("bachelors", "Бакалавриат", ("1", "2", "3", "4")),
    ("masters", "Магистратура", ("1", "2")),
)


def _course_tree(
    pages: list[Page], current_path: str | None, *, home: bool
) -> tuple[list[dict], set[str]]:
    by_path = {page.path: page for page in pages}
    grouped_paths: set[str] = set()
    course_nodes: dict[str, list[dict]] = {}
    visible_course_paths: dict[str, list[str]] = {}
    visible_paths_by_year: dict[str, list[str]] = {}
    for path, degree, year in COURSE_PAGES:
        course_page = by_path.get(path)
        if course_page is None:
            continue
        visible_course_paths.setdefault(degree, []).append(path)
        visible_paths_by_year.setdefault(f"{degree}/{year}", []).append(path)
        grouped_paths.add(path)
        lectures_path = f"{path}/lectures"
        lecture_root = by_path.get(lectures_path)
        lecture_pages = sorted(
            (page for page in pages if page.path.startswith(f"{lectures_path}/")),
            key=lambda page: page.path,
        )
        if lecture_root is not None:
            lecture_pages.insert(0, lecture_root)
            grouped_paths.add(lectures_path)
        grouped_paths.update(page.path for page in lecture_pages)
        other_descendants = [
            page
            for page in pages
            if page.path.startswith(f"{path}/")
            and page.path != lectures_path
            and not page.path.startswith(f"{lectures_path}/")
        ]
        grouped_paths.update(page.path for page in other_descendants)
        other_tree = _decorate_tree(
            _page_tree_from_pages(other_descendants, path), current_path
        )
        lectures_node = {
            "path": lectures_path,
            "title": "Лекции",
            "page_id": None,
            "kind": "folder",
            "current": bool(
                current_path
                and (
                    current_path == lectures_path
                    or current_path.startswith(f"{lectures_path}/")
                )
            ),
            "expanded": bool(
                current_path
                and (
                    current_path == lectures_path
                    or current_path.startswith(f"{lectures_path}/")
                )
            ),
            "tree_id": f"tree{lectures_path.encode().hex()}",
            "children": [
                {
                    "path": page.path,
                    "title": page.title,
                    "page_id": page.id,
                    "kind": "document",
                    "current": page.path == current_path,
                    "expanded": page.path == current_path,
                    "tree_id": f"tree{page.path.encode().hex()}",
                    "children": [],
                }
                for page in lecture_pages
            ]
            or [
                {
                    "path": lectures_path,
                    "title": "Лекции отсутствуют",
                    "page_id": None,
                    "kind": "placeholder",
                    "current": False,
                    "expanded": False,
                    "tree_id": f"empty{lectures_path.encode().hex()}",
                    "children": [],
                }
            ],
        }
        course_nodes.setdefault(f"{degree}/{year}", []).append(
            {
                "path": path,
                "title": course_page.title,
                "page_id": None,
                "kind": "folder",
                "current": current_path == path,
                "expanded": bool(
                    current_path
                    and (current_path == path or current_path.startswith(f"{path}/"))
                ),
                "tree_id": f"course{path.encode().hex()}",
                "children": [
                    {
                        "path": path,
                        "title": "Основная страница",
                        "page_id": course_page.id,
                        "kind": "document",
                        "current": current_path == path,
                        "expanded": current_path == path,
                        "tree_id": f"main{path.encode().hex()}",
                        "children": [],
                    },
                    lectures_node,
                    *other_tree,
                ],
            }
        )

    roots: list[dict] = []
    for degree, title, years in DEGREE_GROUPS:
        active_paths = visible_course_paths.get(degree, [])
        degree_active = any(
            current_path
            and (current_path == path or current_path.startswith(f"{path}/"))
            for path in active_paths
        )
        year_nodes = []
        for year in years:
            path = f"/catalog/{degree}/{year}"
            children = course_nodes.get(f"{degree}/{year}", [])
            year_active = any(
                current_path
                and (
                    current_path == course_path
                    or current_path.startswith(f"{course_path}/")
                )
                for course_path in visible_paths_by_year.get(f"{degree}/{year}", [])
            )
            year_nodes.append(
                {
                    "path": path,
                    "title": f"{year} курс",
                    "page_id": None,
                    "kind": "folder",
                    "current": False,
                    "expanded": bool(
                        year_active or (home and degree == "bachelors" and year == "3")
                    ),
                    "tree_id": f"year{path.encode().hex()}",
                    "children": children,
                }
            )
        roots.append(
            {
                "path": f"/catalog/{degree}",
                "title": title,
                "page_id": None,
                "kind": "folder",
                "current": False,
                "expanded": bool(degree_active or (home and degree == "bachelors")),
                "tree_id": f"degree{degree}",
                "children": year_nodes,
            }
        )
    return roots, grouped_paths


def _page_tree_from_pages(pages: list[Page], root_path: str) -> list[dict]:
    """Build generic visible descendants under a course without losing pages."""
    nodes: dict[str, dict] = {}
    roots: list[dict] = []
    for page in pages:
        parts = page.path.removeprefix(f"{root_path}/").split("/")
        parent_path = root_path
        for index, part in enumerate(parts):
            path = f"{parent_path}/{part}"
            node = nodes.get(path)
            if node is None:
                node = {"path": path, "title": part, "page_id": None, "children": []}
                nodes[path] = node
                if parent_path == root_path:
                    roots.append(node)
                else:
                    nodes[parent_path]["children"].append(node)
            if index == len(parts) - 1:
                node["page_id"] = page.id
                node["title"] = page.title
            parent_path = path
    return roots


def _without_grouped_courses(nodes: list[dict], grouped_paths: set[str]) -> list[dict]:
    filtered: list[dict] = []
    for node in nodes:
        if node["path"] in grouped_paths:
            continue
        children = _without_grouped_courses(node["children"], grouped_paths)
        if node["page_id"] is None and not children:
            continue
        filtered.append({**node, "children": children})
    return filtered


def _navigation_context(
    session: Session,
    scope: PageScope,
    current_path: str | None = None,
    *,
    home: bool = False,
) -> dict:
    visible = visible_pages(session, scope=scope)
    courses, grouped_paths = _course_tree(visible, current_path, home=home)
    generic = _without_grouped_courses(page_tree(session, scope=scope), grouped_paths)
    return {
        "navigation_nodes": courses + _decorate_tree(generic, current_path),
        "visible_tags": visible_tags(session, scope=scope),
    }


@router.get("/pages", response_class=HTMLResponse)
def pages_index(
    request: Request,
    session: SessionDependency,
    scope: ScopeDependency,
    user: HtmlUser,
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
            "current_user": user,
            **_navigation_context(session, scope),
        },
    )


@router.get("/pages/new", response_class=HTMLResponse)
def new_page(
    request: Request,
    session: SessionDependency,
    scope: ScopeDependency,
    user: HtmlEditor,
):
    return templates.TemplateResponse(
        request=request,
        name="pages/editor.html",
        context={
            "page": None,
            "mode": "create",
            "current_user": user,
            **_navigation_context(session, scope),
        },
    )


@router.get("/pages/{page_id}/edit", response_class=HTMLResponse)
def edit_page(
    request: Request,
    page_id: int,
    session: SessionDependency,
    scope: ScopeDependency,
    user: HtmlEditor,
):
    try:
        page = get_page(session, page_id, scope=scope)
    except PageNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    return templates.TemplateResponse(
        request=request,
        name="pages/editor.html",
        context={
            "page": page,
            "mode": "edit",
            "current_user": user,
            **_navigation_context(session, scope),
        },
    )


@router.get("/pages/{page_id}", response_class=HTMLResponse)
def page_by_id(
    request: Request,
    page_id: int,
    session: SessionDependency,
    scope: ScopeDependency,
    user: HtmlUser,
):
    try:
        page = get_page(session, page_id, scope=scope)
    except PageNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    return _render_article(request, page, session, scope, user)


@router.get("/wiki/{page_path:path}", response_class=HTMLResponse)
def page_by_path(
    request: Request,
    page_path: str,
    session: SessionDependency,
    scope: ScopeDependency,
    user: HtmlUser,
):
    try:
        path = validate_page_path(f"/{page_path}")
        page = get_page_by_path(session, path, scope=scope)
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    except PageNotFound as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from error
    return _render_article(request, page, session, scope, user)


def _render_article(
    request: Request, page: Page, session: Session, scope: PageScope, user: User
) -> HTMLResponse:
    sanitized_html, outline = render_document(page.markdown)
    return templates.TemplateResponse(
        request=request,
        name="pages/article.html",
        context={
            "page": page,
            "current_user": user,
            "rendered_html": Markup(sanitized_html),
            "outline": outline,
            "last_modified_display": page.updated_at.astimezone(
                ZoneInfo("Asia/Omsk")
            ).strftime("%d.%m.%Y, %H:%M"),
            **_navigation_context(session, scope, page.path),
        },
    )
