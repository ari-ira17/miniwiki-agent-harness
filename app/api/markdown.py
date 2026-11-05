"""Server-side Markdown preview endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.auth.dependencies import CsrfDependency, require_roles
from app.models.user import User, UserRole
from app.schemas.markdown import MarkdownPreviewRequest, MarkdownPreviewResponse
from app.services.markdown import render_document

router = APIRouter(
    prefix="/api/markdown",
    tags=["markdown"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Sign in to preview Markdown."},
        status.HTTP_403_FORBIDDEN: {
            "description": "Editor role and CSRF token required."
        },
    },
)
EditorUser = Annotated[User, Depends(require_roles(UserRole.ADMIN, UserRole.EDITOR))]


@router.post(
    "/preview",
    response_model=MarkdownPreviewResponse,
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid Markdown or content exceeds 200000 characters."
        }
    },
    summary="Preview sanitized Markdown",
)
def preview_markdown(
    data: MarkdownPreviewRequest, _user: EditorUser, _csrf: CsrfDependency
) -> MarkdownPreviewResponse:
    """Return sanitized HTML using the same pipeline as saved page display."""
    try:
        html, outline = render_document(data.markdown)
        return MarkdownPreviewResponse(html=html, outline=outline)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
