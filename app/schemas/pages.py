"""Page API schemas and canonical path validation."""

import re
from datetime import datetime
from typing import Annotated

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StringConstraints,
    field_validator,
    model_validator,
)

from app.services.tags import normalize_tags

PAGE_PATH_PATTERN = re.compile(
    r"^/(?:[a-z0-9]+(?:-[a-z0-9]+)*)(?:/(?:[a-z0-9]+(?:-[a-z0-9]+)*))*$"
)


def validate_page_path(path: str) -> str:
    """Validate a canonical absolute wiki path without normalizing input."""
    if len(path) > 512 or not PAGE_PATH_PATTERN.fullmatch(path):
        raise ValueError("Path must contain lowercase ASCII slug segments.")
    segments = path[1:].split("/")
    if any(len(segment) > 64 for segment in segments):
        raise ValueError("Path segments must be at most 64 characters.")
    return path


PageTitle = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
PageMarkdown = Annotated[str, StringConstraints(max_length=200_000)]


class PageCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    path: str
    title: PageTitle
    markdown: PageMarkdown = ""
    is_public: bool = False
    tags: list[str] = Field(default_factory=list)

    @field_validator("path")
    @classmethod
    def canonical_path(cls, value: str) -> str:
        return validate_page_path(value)

    @field_validator("tags")
    @classmethod
    def canonical_tags(cls, value: list[str]) -> list[str]:
        return normalize_tags(value)

    @model_validator(mode="after")
    def reconcile_public_tag(self) -> "PageCreate":
        has_public = "public" in self.tags
        public_was_sent = "is_public" in self.model_fields_set
        tags_were_sent = "tags" in self.model_fields_set
        if public_was_sent and tags_were_sent and self.is_public != has_public:
            raise ValueError("is_public must match the public tag.")
        if public_was_sent and self.is_public and not has_public:
            self.tags = normalize_tags([*self.tags, "public"])
            has_public = True
        self.is_public = has_public
        return self


class PageUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: PageTitle | None = None
    markdown: PageMarkdown | None = None
    is_public: bool | None = None
    tags: list[str] | None = None

    @field_validator("title")
    @classmethod
    def non_null_title(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Title cannot be null.")
        return value

    @field_validator("markdown")
    @classmethod
    def non_null_markdown(cls, value: str | None) -> str | None:
        if value is None:
            raise ValueError("Markdown cannot be null.")
        return value

    @field_validator("is_public")
    @classmethod
    def non_null_visibility(cls, value: bool | None) -> bool | None:
        if value is None:
            raise ValueError("Visibility cannot be null.")
        return value

    @field_validator("tags")
    @classmethod
    def non_null_tags(cls, value: list[str] | None) -> list[str] | None:
        if value is None:
            raise ValueError("Tags cannot be null.")
        return normalize_tags(value)

    @model_validator(mode="after")
    def reconcile_public_tag(self) -> "PageUpdate":
        if "tags" not in self.model_fields_set:
            return self
        has_public = "public" in (self.tags or [])
        if "is_public" in self.model_fields_set and self.is_public != has_public:
            raise ValueError("is_public must match the public tag.")
        if "is_public" not in self.model_fields_set:
            self.is_public = has_public
        return self


class PageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    path: str
    title: str
    markdown: str
    is_public: bool
    author_id: int | None
    author_full_name: str | None
    last_editor_id: int | None
    last_editor_full_name: str | None
    created_at: datetime
    updated_at: datetime
    tags: list[str] = Field(validation_alias="tag_names")


class PageList(BaseModel):
    items: list[PageRead]
    total: int
    limit: int
    offset: int


PageLimit = Annotated[int, Field(ge=1, le=100)]
PageOffset = Annotated[int, Field(ge=0)]
