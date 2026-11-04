"""Server-side Markdown preview endpoint."""

from fastapi import APIRouter, HTTPException, status

from app.schemas.markdown import MarkdownPreviewRequest, MarkdownPreviewResponse
from app.services.markdown import render_document

router = APIRouter(prefix="/api/markdown", tags=["markdown"])


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
def preview_markdown(data: MarkdownPreviewRequest) -> MarkdownPreviewResponse:
    """Return sanitized HTML using the same pipeline as saved page display."""
    try:
        html, outline = render_document(data.markdown)
        return MarkdownPreviewResponse(html=html, outline=outline)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error
