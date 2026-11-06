"""Admin-only ZIP export API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response

from app.auth.dependencies import SessionDependency, require_roles
from app.models.user import User, UserRole
from app.services.export import ExportPathConflict, build_export

router = APIRouter(tags=["export"])
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


def export_response(session: SessionDependency) -> Response:
    try:
        content = build_export(session)
    except ExportPathConflict as error:
        raise HTTPException(status_code=409, detail="Export unavailable.") from error
    return Response(
        content=content,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="miniwiki-export.zip"'},
    )


@router.get(
    "/api/export",
    response_class=Response,
    summary="Download all pages as a ZIP archive (admin only)",
    responses={
        200: {
            "description": "ZIP archive of all pages.",
            "content": {
                "application/zip": {"schema": {"type": "string", "format": "binary"}}
            },
            "headers": {
                "Content-Disposition": {
                    "description": "ZIP attachment filename.",
                    "schema": {"type": "string"},
                }
            },
        },
        401: {"description": "Authentication required."},
        403: {"description": "Admin role required."},
        409: {"description": "Export cannot be created."},
    },
)
def export_api(_actor: AdminUser, session: SessionDependency) -> Response:
    return export_response(session)
