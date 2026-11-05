"""Admin-only user management page."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.dependencies import require_html_admin
from app.db import get_session
from app.models.user import User
from app.services.users import list_users

router = APIRouter(include_in_schema=False)
APP_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=APP_DIR / "templates")
SessionDependency = Annotated[Session, Depends(get_session)]
AdminUser = Annotated[User, Depends(require_html_admin)]


@router.get("/users", response_class=HTMLResponse)
def users_page(
    request: Request, actor: AdminUser, session: SessionDependency
) -> HTMLResponse:
    return templates.TemplateResponse(
        request=request,
        name="users/index.html",
        context={"current_user": actor, "users": list_users(session)},
    )
