"""Explicit public request and response contracts."""

import ipaddress
from datetime import date, datetime, timezone
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, HttpUrl, field_validator, model_validator

Alias = Annotated[str, Field(min_length=4, max_length=32, pattern=r"^[A-Za-z0-9_-]+$")]
RESERVED_CODES = {"api", "docs", "redoc", "health", "openapi", "favicon"}


def validate_target(url: HttpUrl) -> HttpUrl:
    if url.username or url.password:
        raise ValueError("Credentials in target URLs are not permitted")
    host = (url.host or "").lower().rstrip(".")
    if host in {"localhost", "localhost.localdomain"} or host.endswith((".local", ".internal")):
        raise ValueError("Local hostnames are not permitted")
    try:
        address = ipaddress.ip_address(host.strip("[]"))
    except ValueError:
        pass
    else:
        if not address.is_global:
            raise ValueError("Non-public IP addresses are not permitted")
    if len(str(url)) > 2048:
        raise ValueError("Target URLs must be at most 2048 characters")
    return url


def validate_alias(value: str) -> str:
    if value.casefold() in RESERVED_CODES:
        raise ValueError("This alias is reserved")
    return value


class LinkCreate(BaseModel):
    target_url: HttpUrl
    alias: Alias | None = None
    expires_at: datetime | None = None

    @field_validator("target_url")
    @classmethod
    def valid_target(cls, value: HttpUrl) -> HttpUrl:
        return validate_target(value)

    @field_validator("alias")
    @classmethod
    def valid_alias(cls, value: str | None) -> str | None:
        return validate_alias(value) if value is not None else None

    @model_validator(mode="after")
    def future_expiry(self) -> Self:
        if self.expires_at is not None:
            if self.expires_at.tzinfo is None or self.expires_at <= datetime.now(timezone.utc):
                raise ValueError("expires_at must be a future timezone-aware timestamp")
        return self


class LinkUpdate(BaseModel):
    is_active: bool | None = None
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def valid_update(self) -> Self:
        if "is_active" in self.model_fields_set and self.is_active is None:
            raise ValueError("is_active cannot be null")
        if self.expires_at is not None:
            if self.expires_at.tzinfo is None or self.expires_at <= datetime.now(timezone.utc):
                raise ValueError("expires_at must be a future timezone-aware timestamp")
        return self


class LinkRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    target_url: str
    short_url: str
    is_active: bool
    expires_at: datetime | None
    created_at: datetime
    updated_at: datetime
    click_count: int
    last_accessed_at: datetime | None


class LinkPage(BaseModel):
    items: list[LinkRead]
    total: int
    limit: int
    offset: int


class DailyStat(BaseModel):
    day: date
    clicks: int


class LinkStats(BaseModel):
    code: str
    total_clicks: int
    last_accessed_at: datetime | None
    daily: list[DailyStat]


class TopLink(BaseModel):
    code: str
    clicks: int


class SummaryStats(BaseModel):
    total_links: int
    total_clicks: int
    top_links: list[TopLink]
