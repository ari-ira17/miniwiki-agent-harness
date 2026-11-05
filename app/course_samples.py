"""Idempotently add missing public course pages and local reading material."""

from pathlib import Path

from sqlalchemy import select

from app.bootstrap import ensure_initial_admin
from app.db import get_session_factory
from app.models.page import Page
from app.schemas.pages import PageCreate
from app.services.pages import create_page

CONTENT_DIR = Path(__file__).resolve().parent / "content"


def _content(filename: str) -> str:
    return (CONTENT_DIR / filename).read_text(encoding="utf-8")


COURSES: tuple[PageCreate, ...] = (
    PageCreate(
        path="/disciplines/nlp",
        title="Обработка естественного языка",
        tags=["public", "nlp", "deep learning", "machine learning"],
        markdown=_content("nlp.md"),
    ),
    PageCreate(
        path="/disciplines/programming-workshop-bachelors-5sem",
        title="Практикум по программированию (5 семестр)",
        tags=["public", "machine learning"],
        markdown=_content("programming-workshop-bachelors-5sem.md"),
    ),
    PageCreate(
        path="/disciplines/nlp/lectures/preprocessing",
        title="Предварительная обработка текстовых данных (2025)",
        tags=["public", "nlp"],
        markdown=_content("preprocessing.md"),
    ),
)


def seed_course_pages() -> tuple[list[str], list[str]]:
    """Create missing course pages without overwriting any existing content."""
    factory = get_session_factory()
    ensure_initial_admin(factory)
    created: list[str] = []
    existing: list[str] = []
    with factory() as session:
        for data in COURSES:
            if (
                session.scalar(select(Page.id).where(Page.path == data.path))
                is not None
            ):
                existing.append(data.path)
                continue
            create_page(session, data)
            created.append(data.path)
    return created, existing


def main() -> None:
    created, existing = seed_course_pages()
    for path in created:
        print(f"Created course page: {path}")
    for path in existing:
        print(f"Preserved existing page: {path}")


if __name__ == "__main__":
    main()
