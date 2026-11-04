"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, status
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from starlette.requests import Request
from starlette.responses import JSONResponse

from app.api.markdown import router as markdown_router
from app.api.navigation import router as navigation_router
from app.api.pages import router as pages_router
from app.bootstrap import ensure_initial_admin
from app.db import check_database, get_session_factory
from app.web.pages import router as web_pages_router

APP_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=APP_DIR / "templates")


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await run_in_threadpool(ensure_initial_admin, get_session_factory())
    yield


app = FastAPI(title="MiniWiki", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
app.include_router(pages_router)
app.include_router(navigation_router)
app.include_router(markdown_router)
app.include_router(web_pages_router)


class HealthResponse(BaseModel):
    status: str


@app.get("/", include_in_schema=False)
def home(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="home.html",
        context={},
    )


@app.get(
    "/health",
    tags=["health"],
    response_model=HealthResponse,
    responses={
        status.HTTP_503_SERVICE_UNAVAILABLE: {
            "model": HealthResponse,
            "description": "Database is unavailable.",
        }
    },
)
def health() -> HealthResponse | JSONResponse:
    """Report readiness only when PostgreSQL accepts a simple query."""
    try:
        check_database()
    except SQLAlchemyError:
        return JSONResponse(
            content={"status": "unavailable"},
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )
    return HealthResponse(status="ok")
