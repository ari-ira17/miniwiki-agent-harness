"""Search and navigation response schemas."""

from pydantic import BaseModel, Field


class TreeNode(BaseModel):
    path: str
    title: str
    page_id: int | None
    children: list["TreeNode"] = Field(default_factory=list)


TreeNode.model_rebuild()
