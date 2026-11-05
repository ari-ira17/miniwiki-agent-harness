"""Environment based application settings."""

from functools import lru_cache
from typing import Annotated

from pydantic import Field, SecretStr, StringConstraints, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL

from app.profiles import validate_person_name


class Settings(BaseSettings):
    """Runtime configuration; secrets are never included in repr output."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        repr=False,
        hide_input_in_errors=True,
    )

    postgres_user: str = Field(validation_alias="POSTGRES_USER")
    postgres_password: SecretStr = Field(validation_alias="POSTGRES_PASSWORD")
    postgres_db: str = Field(validation_alias="POSTGRES_DB")
    postgres_host: str = Field(default="db", validation_alias="POSTGRES_HOST")
    postgres_port: int = Field(default=5432, validation_alias="POSTGRES_PORT")
    admin_username: str = Field(
        min_length=1, max_length=64, validation_alias="ADMIN_USERNAME"
    )
    admin_password: SecretStr = Field(
        min_length=12, max_length=256, validation_alias="ADMIN_PASSWORD"
    )
    admin_first_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ] = Field(validation_alias="ADMIN_FIRST_NAME")
    admin_last_name: Annotated[
        str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)
    ] = Field(validation_alias="ADMIN_LAST_NAME")

    @field_validator("admin_first_name", "admin_last_name")
    @classmethod
    def valid_admin_names(cls, value: str) -> str:
        return validate_person_name(value)

    session_cookie_secure: bool = Field(
        default=False, validation_alias="SESSION_COOKIE_SECURE"
    )

    @property
    def database_url(self) -> str:
        """Build a correctly escaped SQLAlchemy URL from individual env fields."""
        return URL.create(
            "postgresql+psycopg",
            username=self.postgres_user,
            password=self.postgres_password.get_secret_value(),
            host=self.postgres_host,
            port=self.postgres_port,
            database=self.postgres_db,
            query={"connect_timeout": "3"},
        ).render_as_string(hide_password=False)


@lru_cache
def get_settings() -> Settings:
    return Settings()
