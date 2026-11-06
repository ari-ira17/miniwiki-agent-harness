"""Admin-only browser download for the wiki export."""

from typing import Annotated

from fastapi import APIRouter, Depends, Response

from app.api.export import export_response
from app.auth.dependencies import SessionDependency, require_html_admin
from app.models.user import User

router = APIRouter(include_in_schema=False)
AdminUser = Annotated[User, Depends(require_html_admin)]


@router.get("/export")
def export_page(_actor: AdminUser, session: SessionDependency) -> Response:
    return export_response(session)
