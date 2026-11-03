"""FastAPI application entry point."""


from fastapi import FastAPI, status
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError
from starlette.responses import JSONResponse

from app.db import check_database

app = FastAPI(title="MiniWiki", version="0.1.0")


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
