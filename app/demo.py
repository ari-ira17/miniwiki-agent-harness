"""Idempotently add demonstration pages to the configured local database."""

from sqlalchemy import select
from sqlalchemy.orm import sessionmaker

from app.db import get_session_factory
from app.models.page import Page
from app.schemas.pages import PageCreate
from app.services.pages import create_page

DEMO_PAGES = [
    PageCreate(
        path="/demo/linguistics",
        title="Лингвистика",
        markdown="# Лингвистика\n\nРаздел о языке и корпусах.",
        is_public=True,
        tags=["демо", "лингвистика", "public"],
    ),
    PageCreate(
        path="/demo/linguistics/search",
        title="Поиск по корпусу",
        markdown="## Подготовка корпуса\n\nОчистите и разметьте тексты.\n\n"
        "## Поиск\n\nСравните запросы по заголовку и содержимому.",
        is_public=True,
        tags=["демо", "поиск", "public"],
    ),
    PageCreate(
        path="/demo/linguistics/tags",
        title="Справочник тегов",
        markdown="## Тематические теги\n\nОбщие теги объединяют близкие материалы.",
        tags=["демо", "теги"],
    ),
    PageCreate(
        path="/demo/long-article",
        title="Большая демонстрационная статья",
        markdown="\n\n".join(
            f"## Раздел {index}: заметки о поиске\n\n"
            + "Вложенная документация помогает проверить оглавление, прокрутку и ссылки. "
            * 18
            + f"\n\n#### Подраздел {index}: дополнительные замечания\n\n"
            + "Материалы остаются читаемыми при длинной навигации. " * 8
            for index in range(1, 35)
        ),
        tags=["демо", "длинная статья"],
    ),
]


def seed_demo(session_factory: sessionmaker | None = None) -> list[str]:
    """Create only missing demo paths and leave existing records untouched."""
    created_paths: list[str] = []
    factory = session_factory or get_session_factory()
    with factory() as session:
        for data in DEMO_PAGES:
            exists = session.scalar(select(Page.id).where(Page.path == data.path))
            if exists is None:
                create_page(session, data)
                created_paths.append(data.path)
    return created_paths


if __name__ == "__main__":
    created = seed_demo()
    print(f"Created {len(created)} demo pages; existing pages were left unchanged.")
