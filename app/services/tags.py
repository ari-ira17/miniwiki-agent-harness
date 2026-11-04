"""Canonical tag validation and persistence helpers."""

import unicodedata

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.tag import Tag

MAX_TAGS_PER_PAGE = 20
MAX_TAG_LENGTH = 32


def normalize_tag(value: str) -> str:
    """Trim a tag and normalize it for case-insensitive identity."""
    name = unicodedata.normalize("NFC", value).strip().casefold()
    if (
        not name
        or len(name) > MAX_TAG_LENGTH
        or "," in name
        or any(unicodedata.category(char).startswith("C") for char in name)
    ):
        raise ValueError("Tags must contain 1–32 characters.")
    return name


def normalize_tags(values: list[str]) -> list[str]:
    """Return unique canonical tags, preserving their first appearance."""
    names = list(dict.fromkeys(normalize_tag(value) for value in values))
    if len(names) > MAX_TAGS_PER_PAGE:
        raise ValueError("A page can have at most 20 tags.")
    return names


def get_or_create_tags(session: Session, names: list[str]) -> list[Tag]:
    """Resolve canonical tags, creating missing entries within the transaction."""
    tags: list[Tag] = []
    for name in sorted(names):
        session.execute(
            insert(Tag)
            .values(name=name)
            .on_conflict_do_nothing(index_elements=[Tag.name])
        )
        tags.append(session.scalar(select(Tag).where(Tag.name == name)))
    return tags
