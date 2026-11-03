"""FastAPI application entry point."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from starlette.concurrency import run_in_threadpool
from starlette.responses import JSONResponse

from app.bootstrap import ensure_initial_admin
from app.db import check_database, get_session_factory

@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    await run_in_threadpool(ensure_initial_admin, get_session_factory())
    yield


app = FastAPI(title="MiniWiki", version="0.1.0", lifespan=lifespan)


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
