"""Constant-time API key authentication. Do not log credentials."""

import hmac
from typing import Annotated

from fastapi import Depends, HTTPException, Security
from fastapi.security import APIKeyHeader

from shortlink.config import Settings, get_settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


def require_admin(
    api_key: Annotated[str | None, Security(api_key_header)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    if api_key is None or not api_key.isascii() or not hmac.compare_digest(api_key, settings.admin_api_key):
        raise HTTPException(status_code=401, detail="Invalid API key")
    return "admin"
