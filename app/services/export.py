"""Build a complete ZIP archive of wiki pages."""

import json
from io import BytesIO
from zipfile import ZIP_DEFLATED, ZipFile

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models.page import Page
from app.schemas.pages import validate_page_path


class ExportPathConflict(Exception):
    """A persisted path cannot be represented safely in the archive."""


def _yaml_json(value: object) -> str:
    """Encode JSON-compatible YAML while escaping YAML-sensitive characters."""
    encoded = json.dumps(value, ensure_ascii=False)
    return "".join(
        f"\\u{ord(char):04x}"
        if 0x7F <= ord(char) <= 0x9F or ord(char) in (0x2028, 0x2029, 0xFFFE, 0xFFFF)
        else char
        for char in encoded
    )


def build_export(session: Session) -> bytes:
    """Read all pages and tags in one query, validate paths, and build the ZIP."""
    pages = (
        session.scalars(select(Page).options(joinedload(Page.tags)).order_by(Page.path))
        .unique()
        .all()
    )
    entries = []
    names = set()
    for page in pages:
        try:
            path = validate_page_path(page.path)
        except (ValueError, TypeError) as error:
            raise ExportPathConflict from error
        name = f"{path[1:]}.md"
        if name in names:
            raise ExportPathConflict
        names.add(name)
        entries.append((name, page))

    output = BytesIO()
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for name, page in entries:
            frontmatter = (
                f"---\ntitle: {_yaml_json(page.title)}\n"
                f"tags: {_yaml_json(page.tag_names)}\n---\n"
            )
            archive.writestr(name, (frontmatter + page.markdown).encode("utf-8"))
    return output.getvalue()
