"""Environment-driven application settings."""

from functools import lru_cache

from pydantic import Field, HttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.engine import URL


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SHORTLINK_", env_file=".env", extra="ignore")

    database_url: str = ""
    db_host: str = "db"
    db_port: int = Field(default=5432, ge=1, le=65535)
    db_user: str = "shortlink"
    db_name: str = "shortlink"
    db_password: str | None = Field(default=None, repr=False)
    admin_api_key: str = Field(min_length=32, repr=False)
    base_url: HttpUrl = HttpUrl("http://localhost:8000/")
    max_requests_per_minute: int = Field(default=60, ge=1, le=10000)

    @field_validator("admin_api_key")
    @classmethod
    def validate_admin_key(cls, value: str) -> str:
        if value.startswith("replace-with-"):
            raise ValueError("Replace the example API key before starting the server")
        if not value.isascii():
            raise ValueError("The admin API key must contain ASCII characters only")
        return value

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: str) -> str:
        if value and not value.startswith("postgresql+psycopg://"):
            raise ValueError("Use a postgresql+psycopg:// database URL")
        return value

    @model_validator(mode="after")
    def resolve_database_url(self) -> "Settings":
        """Use a URL-encoded DSN while preserving the original database password."""
        if self.database_url:
            return self
        if not self.db_password:
            raise ValueError("Set SHORTLINK_DATABASE_URL or SHORTLINK_DB_PASSWORD")
        self.database_url = URL.create(
            "postgresql+psycopg",
            username=self.db_user,
            password=self.db_password,
            host=self.db_host,
            port=self.db_port,
            database=self.db_name,
        ).render_as_string(hide_password=False)
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
