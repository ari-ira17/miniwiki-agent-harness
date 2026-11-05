"""User administration request and response schemas."""

import re
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    SecretStr,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.auth.usernames import canonicalize_username
from app.models.user import UserRole
from app.profiles import validate_person_name

Username = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=64),
]
PersonName = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=100),
]
NewPassword = Annotated[SecretStr, Field(min_length=12, max_length=256)]


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    username: Username
    first_name: PersonName
    last_name: PersonName
    password: NewPassword
    role: UserRole

    @field_validator("username")
    @classmethod
    def canonical_username(cls, value: str) -> str:
        username = canonicalize_username(value)
        if not re.fullmatch(r"[\w.-]{1,64}", username, flags=re.UNICODE):
            raise ValueError("Use letters, numbers, dots, underscores or hyphens.")
        return username

    @field_validator("first_name", "last_name")
    @classmethod
    def valid_person_names(cls, value: str) -> str:
        return validate_person_name(value)


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid", hide_input_in_errors=True)

    role: UserRole | None = None
    is_active: bool | None = None
    first_name: PersonName | None = None
    last_name: PersonName | None = None
    password: NewPassword | None = None

    @field_validator("role", "is_active", "first_name", "last_name", "password")
    @classmethod
    def reject_null(cls, value):
        if value is None:
            raise ValueError("Value cannot be null.")
        return value

    @field_validator("first_name", "last_name")
    @classmethod
    def valid_person_names(cls, value: str) -> str:
        return validate_person_name(value)

    @model_validator(mode="after")
    def require_change(self) -> "UserUpdate":
        if not self.model_fields_set:
            raise ValueError("At least one user field must be changed.")
        return self


class UserRead(BaseModel):
    id: int
    username: str
    first_name: str
    last_name: str
    full_name: str
    role: UserRole
    is_active: bool

    model_config = ConfigDict(from_attributes=True)
