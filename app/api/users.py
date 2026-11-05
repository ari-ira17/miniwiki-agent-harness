"""Admin-only user account API."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.auth.dependencies import CsrfDependency, require_roles
from app.db import get_session
from app.models.user import User, UserRole
from app.schemas.users import UserCreate, UserRead, UserUpdate
from app.services import users as user_service

router = APIRouter(
    prefix="/api/users",
    tags=["users"],
    responses={
        status.HTTP_401_UNAUTHORIZED: {"description": "Authentication required."},
        status.HTTP_403_FORBIDDEN: {
            "description": "Admin role required or CSRF failed."
        },
    },
)
SessionDependency = Annotated[Session, Depends(get_session)]
AdminUser = Annotated[User, Depends(require_roles(UserRole.ADMIN))]


def _raise_service_error(error: Exception) -> None:
    if isinstance(error, user_service.UserNotFound):
        raise HTTPException(status_code=404, detail="User not found.") from error
    if isinstance(error, user_service.UsernameConflict):
        raise HTTPException(
            status_code=409, detail="Username is already in use."
        ) from error
    if isinstance(error, user_service.LastActiveAdmin):
        raise HTTPException(
            status_code=409,
            detail="The last active administrator cannot be removed or demoted.",
        ) from error
    if isinstance(error, user_service.ActorNoLongerAdmin):
        raise HTTPException(
            status_code=403, detail="Admin permission is no longer active."
        ) from error
    raise error


@router.get("", response_model=list[UserRead], summary="List users")
def list_users(_actor: AdminUser, session: SessionDependency) -> list[UserRead]:
    return user_service.list_users(session)


@router.post(
    "",
    response_model=UserRead,
    status_code=status.HTTP_201_CREATED,
    responses={
        status.HTTP_409_CONFLICT: {"description": "Username already exists."},
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid username, role or password."
        },
    },
    summary="Create a user",
)
def create_user(
    data: UserCreate,
    actor: AdminUser,
    _csrf: CsrfDependency,
    session: SessionDependency,
) -> UserRead:
    try:
        return user_service.create_user(session, actor.id, data)
    except (
        user_service.UsernameConflict,
        user_service.ActorNoLongerAdmin,
    ) as error:
        _raise_service_error(error)


@router.patch(
    "/{user_id}",
    response_model=UserRead,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "User not found."},
        status.HTTP_409_CONFLICT: {
            "description": "The last active administrator is protected."
        },
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": "Invalid or empty user update."
        },
    },
    summary="Update a user",
)
def update_user(
    user_id: int,
    data: UserUpdate,
    actor: AdminUser,
    _csrf: CsrfDependency,
    session: SessionDependency,
) -> UserRead:
    try:
        return user_service.update_user(session, actor.id, user_id, data)
    except (
        user_service.UserNotFound,
        user_service.LastActiveAdmin,
        user_service.ActorNoLongerAdmin,
    ) as error:
        _raise_service_error(error)


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses={
        status.HTTP_404_NOT_FOUND: {"description": "User not found."},
        status.HTTP_409_CONFLICT: {
            "description": "The last active administrator is protected."
        },
    },
    summary="Delete a user",
)
def delete_user(
    user_id: int,
    actor: AdminUser,
    _csrf: CsrfDependency,
    session: SessionDependency,
) -> Response:
    try:
        user_service.delete_user(session, actor.id, user_id)
    except (
        user_service.UserNotFound,
        user_service.LastActiveAdmin,
        user_service.ActorNoLongerAdmin,
    ) as error:
        _raise_service_error(error)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
