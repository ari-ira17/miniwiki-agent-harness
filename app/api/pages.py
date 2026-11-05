"""REST endpoints for hierarchical wiki pages."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import (
    CsrfDependency,
    CurrentUser,
    page_scope_for,
    require_roles,
)
from app.db import get_session
from app.models.user import User, UserRole
from app.schemas.pages import (
    PageCreate,
    PageLimit,
    PageList,
    PageOffset,
    PageRead,
    PageUpdate,
    validate_page_path,
)
from app.services import pages as page_service
from app.services.permissions import PageScope
from app.services.search import search_pages

router = APIRouter(
    prefix="/api/pages",
    tags=["pages"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Sign in to access pages."},
        status.HTTP_403_FORBIDDEN: {
            "description": "Editor role and CSRF token required for changes."
        },
    },
)
SessionDependency = Annotated[Session, Depends(get_session)]


def get_page_scope(user: CurrentUser) -> PageScope:
    return page_scope_for(user)


ScopeDependency = Annotated[PageScope, Depends(get_page_scope)]
EditorUser = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.EDITOR))]


def _not_found() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND, detail="Page not found."
    )


@router.post(
    "",
    response_model=PageRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {"description": "The path is already in use."},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {"description": "Invalid page data."},
    },
    summary="Create a page",
)
def create_page(
    data: PageCreate,
    session: SessionDependency,
    user: EditorUser,
    _csrf: CsrfDependency,
) -> PageRead:
    """Create a page at an unused canonical path."""
    try:
        return page_service.create_page(
            session, data, author_id=user.id, last_editor_id=user.id
        )
    except page_service.PagePathConflict as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Page path is already in use."
        ) from error


@router.get("", response_model=PageList, summary="List pages")
def list_pages(
    session: SessionDependency,
    scope: ScopeDependency,
    limit: PageLimit = 50,
    offset: PageOffset = 0,
    q: Annotated[str, Query(max_length=200)] = "",
    tag: Annotated[str | None, Query(max_length=32)] = None,
) -> PageList:
    """Search title/body and filter by a tag, ordered with bounded pagination."""
    try:
        pages, total = search_pages(
            session, query=q, tag=tag, limit=limit, offset=offset, scope=scope
        )
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return PageList(items=pages, total=total, limit=limit, offset=offset)


@router.get(
    "/by-path",
    response_model=PageRead,
    responses={status.HTTP_404_NOT_FOUND: {"description": "Page not found."}},
    summary="Read a page by path",
)
def read_page_by_path(
    path: Annotated[str, Query(description="Canonical path, for example /docs/nlp")],
    session: SessionDependency,
    scope: ScopeDependency,
) -> PageRead:
    """Read one page by its canonical hierarchy path."""
    try:
        path = validate_page_path(path)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
    try:
        return page_service.get_page_by_path(session, path, scope=scope)
    except page_service.PageNotFound as error:
        raise _not_found() from error


@router.get(
    "/{page_id}",
    response_model=PageRead,
    responses={status.HTTP_404_NOT_FOUND: {"description": "Page not found."}},
    summary="Read a page",
)
def read_page(
    page_id: int, session: SessionDependency, scope: ScopeDependency
) -> PageRead:
    """Read one page by its numeric id."""
    try:
        return page_service.get_page(session, page_id, scope=scope)
    except page_service.PageNotFound as error:
        raise _not_found() from error


@router.patch(
    "/{page_id}",
    response_model=PageRead,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "Page not found."},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid or empty patch. The path cannot be changed."
        },
    },
    summary="Edit a page",
)
def update_page(
    page_id: int,
    data: PageUpdate,
    session: SessionDependency,
    user: EditorUser,
    _csrf: CsrfDependency,
) -> PageRead:
    """Edit page content or visibility while keeping its path unchanged."""
    try:
        return page_service.update_page(session, page_id, data, editor_id=user.id)
    except page_service.PageNotFound as error:
        raise _not_found() from error
    except page_service.EmptyPageUpdate as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="At least one editable field is required.",
        ) from error


@router.delete(
    "/{page_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={status.HTTP_404_NOT_FOUND: {"description": "Page not found."}},
    summary="Delete a page",
)
def delete_page(
    page_id: int,
    session: SessionDependency,
    _user: EditorUser,
    _csrf: CsrfDependency,
) -> Response:
    """Delete one page without affecting descendants in the path hierarchy."""
    try:
        page_service.delete_page(session, page_id)
    except page_service.PageNotFound as error:
        raise _not_found() from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)
