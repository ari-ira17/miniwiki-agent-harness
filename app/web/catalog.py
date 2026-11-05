"""Public course catalog and authenticated page-tree context for home."""

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.auth.dependencies import AuthSessionDependency, page_scope_for
from app.db import get_session
from app.models.user import User
from app.web.pages import _navigation_context

router = APIRouter(include_in_schema=False)
APP_DIR = Path(__file__).resolve().parents[1]
templates = Jinja2Templates(directory=APP_DIR / "templates")
SessionDependency = Annotated[Session, Depends(get_session)]


CATALOG = (
    {
        "title": "Бакалавриат",
        "id": "bachelors",
        "courses": (
            {
                "title": "1 Курс",
                "items": (("Аппаратные средства вычислительной техники", "/"),),
            },
            {
                "title": "2 Курс",
                "items": (
                    ("Машинное обучение", "/"),
                    ("ООАиП", "/"),
                    ("Разработка операционных систем", "/"),
                ),
            },
            {
                "title": "3 Курс",
                "items": (
                    (
                        "Практикум по программированию 5-й семестр",
                        "/wiki/disciplines/programming-workshop-bachelors-5sem",
                    ),
                    ("Практикум по программированию 6-й семестр (МО)", "/"),
                    ("Обработка естественного языка", "/wiki/disciplines/nlp"),
                    ("SQL и получение данных", "/"),
                    ("Технологии больших данных", "/"),
                    ("Разработка web-приложений", "/"),
                    ("Администрирование баз данных", "/"),
                    ("Анализ временных рядов", "/"),
                    ("Компьютерное зрение", "/"),
                ),
            },
            {
                "title": "4 Курс",
                "items": (
                    ("Разработка высоконагруженных приложений", "/"),
                    ("Тестирование программного обеспечения", "/"),
                    ("DevOps-инженерия", "/"),
                    ("Продвинутые методы работы с данными", "/"),
                ),
            },
        ),
    },
    {
        "title": "Магистратура",
        "id": "masters",
        "courses": (
            {
                "title": "1 Курс",
                "items": (
                    ("Практикум по программированию", "/"),
                    ("Глубокое обучение", "/"),
                    ("Учебная практика (ИМ СО РАН)", "/"),
                ),
            },
            {
                "title": "2 Курс",
                "items": (
                    ("Администрирование больших данных", "/"),
                    ("Высокопроизводительная обработка и анализ данных", "/"),
                ),
            },
        ),
    },
    {
        "title": "Элективные дисциплины",
        "id": "electives",
        "courses": (),
        "items": (("Графы и магические квадраты: олимпиадные задачи на Python", "/"),),
    },
)


@router.get("/", response_class=HTMLResponse)
def course_catalog(
    request: Request,
    session: SessionDependency,
    auth_session: AuthSessionDependency,
) -> HTMLResponse:
    user: User | None = auth_session.user if auth_session else None
    navigation_nodes = (
        _navigation_context(session, page_scope_for(user), home=True)[
            "navigation_nodes"
        ]
        if user
        else None
    )
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={
            "catalog": CATALOG,
            "current_user": user,
            "navigation_nodes": navigation_nodes,
        },
    )
