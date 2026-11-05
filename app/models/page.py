"""Wiki page model."""

from datetime import UTC, datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.tag import Tag
    from app.models.user import User


def utc_now() -> datetime:
    """Return a timezone-aware UTC timestamp."""
    return datetime.now(UTC)


class Page(Base):
    __tablename__ = "pages"
    __table_args__ = (Index("ix_pages_path", "path", unique=True),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    path: Mapped[str] = mapped_column(String(512), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    markdown: Mapped[str] = mapped_column(Text, nullable=False, default="")
    author_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    last_editor_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=utc_now, onupdate=utc_now
    )
    tags: Mapped[list["Tag"]] = relationship(
        secondary="page_tags", back_populates="pages", order_by="Tag.name"
    )
    author: Mapped["User | None"] = relationship(foreign_keys=[author_id])
    last_editor: Mapped["User | None"] = relationship(foreign_keys=[last_editor_id])

    @property
    def tag_names(self) -> list[str]:
        return [tag.name for tag in self.tags]

    @property
    def is_public(self) -> bool:
        """Compatibility view of the canonical public tag."""
        return "public" in self.tag_names

    @property
    def author_full_name(self) -> str | None:
        return self.author.full_name if self.author is not None else None

    @property
    def last_editor_full_name(self) -> str | None:
        return self.last_editor.full_name if self.last_editor is not None else None
