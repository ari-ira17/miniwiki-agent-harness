"""Markdown preview API schemas."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints


class MarkdownPreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    markdown: Annotated[str, StringConstraints(max_length=200_000)]


class MarkdownPreviewResponse(BaseModel):
    html: str
    outline: list[dict[str, int | str]]
