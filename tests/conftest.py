"""PostgreSQL-backed integration fixtures; use a disposable database only."""

from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from shortlink.config import get_settings
from shortlink.db import get_engine
from shortlink.main import app
from shortlink.models import DailyClick, Link
from shortlink.rate_limit import limiter


@pytest.fixture(autouse=True)
def clean_database() -> Iterator[None]:
    # Explicit guard to prevent accidentally clearing a production database.
    database = make_url(get_settings().database_url).database or ""
    if not database.endswith("_test"):
        raise RuntimeError("Tests require a disposable database named with the _test suffix")
    with Session(get_engine()) as db:
        db.execute(delete(DailyClick))
        db.execute(delete(Link))
        db.commit()
    limiter._times.clear()
    yield
    app.dependency_overrides.clear()
    with Session(get_engine()) as db:
        db.execute(delete(DailyClick))
        db.execute(delete(Link))
        db.commit()


@pytest.fixture
def client() -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth() -> dict[str, str]:
    return {"X-API-Key": get_settings().admin_api_key}
