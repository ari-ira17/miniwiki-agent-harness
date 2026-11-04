"""Search facets and hierarchical navigation API."""

from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.pages import get_page_scope
from app.db import get_session
from app.schemas.navigation import TreeNode
from app.services.navigation import page_tree, visible_tags
from app.services.permissions import PageScope

router = APIRouter(prefix="/api", tags=["navigation"])
SessionDependency = Annotated[Session, Depends(get_session)]
ScopeDependency = Annotated[PageScope, Depends(get_page_scope)]


@router.get("/tags", response_model=list[str], summary="List visible tags")
def list_tags(session: SessionDependency, scope: ScopeDependency) -> list[str]:
    """List tags attached to pages visible to the current principal."""
    return visible_tags(session, scope=scope)


@router.get(
    "/navigation/tree", response_model=list[TreeNode], summary="Get visible page tree"
)
def get_navigation_tree(
    session: SessionDependency, scope: ScopeDependency
) -> list[dict]:
    """Return visible pages and virtual path branches as a nested tree."""
    return page_tree(session, scope=scope)
