"""Environment-driven application settings."""

from functools import lru_cache

from pydantic import Field, HttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SHORTLINK_", env_file=".env", extra="ignore")

    database_url: str
    admin_api_key: str = Field(min_length=32)
    base_url: HttpUrl = HttpUrl("http://localhost:8000/")
    max_requests_per_minute: int = Field(default=60, ge=1, le=10000)

    @field_validator("admin_api_key")
    @classmethod
    def reject_placeholder(cls, value: str) -> str:
        if value.startswith("replace-with-"):
            raise ValueError("Replace the example API key before starting the server")
        return value

    @field_validator("database_url")
    @classmethod
    def postgres_only(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("Use a postgresql+psycopg:// database URL")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
