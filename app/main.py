"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, status
from fastapi.exception_handlers import request_validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from app.api.auth import router as auth_router
from app.api.export import router as export_router
from app.api.markdown import router as markdown_router
from app.api.navigation import router as navigation_router
from app.api.pages import router as pages_router
from app.api.users import router as users_router
from app.bootstrap import ensure_initial_admin
from app.db import check_database, get_session_factory
from app.web.auth import router as web_auth_router
from app.web.catalog import router as catalog_router
from app.web.export import router as web_export_router
from app.web.pages import router as web_pages_router
from app.web.users import router as web_users_router

APP_DIR = Path(__file__).resolve().parent


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await run_in_threadpool(ensure_initial_admin, get_session_factory())
    yield


app = FastAPI(title="MiniWiki", version="0.1.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=APP_DIR / "static"), name="static")
app.include_router(export_router)
app.include_router(pages_router)
app.include_router(auth_router)
app.include_router(users_router)
app.include_router(navigation_router)
app.include_router(markdown_router)
app.include_router(web_export_router)
app.include_router(catalog_router)
app.include_router(web_pages_router)
app.include_router(web_auth_router)
app.include_router(web_users_router)


@app.exception_handler(RequestValidationError)
async def safe_validation_errors(request: Request, exc: RequestValidationError):
    if request.url.path == "/api/auth/login" or request.url.path.startswith(
        "/api/users"
    ):
        safe_errors = [
            {
                "loc": error.get("loc", ()),
                "msg": error.get("msg", "Invalid value."),
                "type": error.get("type", "value_error"),
            }
            for error in exc.errors()
        ]
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": safe_errors},
        )
    return await request_validation_exception_handler(request, exc)


@app.middleware("http")
async def secure_response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers.setdefault("Cache-Control", "no-store")
    response.headers.setdefault("Referrer-Policy", "same-origin")
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    return response


class HealthResponse(BaseModel):
    status: str


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
