"""End-to-end behavior against migrated PostgreSQL."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shortlink.config import get_settings
from shortlink.db import get_engine, get_session
from shortlink.main import app
from shortlink.models import DailyClick, Link
from shortlink.rate_limit import RateLimiter


def create(client: TestClient, auth: dict[str, str], **kwargs: object):
    payload = {"target_url": "https://example.org/articles", **kwargs}
    return client.post("/api/v1/links", headers=auth, json=payload)


def test_health_and_docs(client: TestClient) -> None:
    assert client.get("/health").json() == {"status": "ok"}
    assert client.get("/docs").status_code == 200
    assert "/api/v1/links" in client.get("/openapi.json").json()["paths"]


def test_authentication_required(client: TestClient, auth: dict[str, str]) -> None:
    for path in ["/api/v1/links", "/api/v1/analytics"]:
        assert client.get(path).status_code == 401
        assert client.get(path, headers={"X-API-Key": "wrong"}).status_code == 401
    assert (
        client.post("/api/v1/links", json={"target_url": "https://example.org"}).status_code == 401
    )
    assert client.get("/api/v1/links", headers=auth).status_code == 200


def test_create_and_lookup(client: TestClient, auth: dict[str, str]) -> None:
    result = create(client, auth)
    assert result.status_code == 201
    link = result.json()
    assert len(link["code"]) == 7
    assert link["short_url"].endswith("/" + link["code"])
    assert link["click_count"] == 0
    assert link["last_accessed_at"] is None
    found = client.get("/api/v1/links/" + link["code"], headers=auth)
    assert found.status_code == 200
    assert found.json()["target_url"] == "https://example.org/articles"


def test_redirect_and_analytics(client: TestClient, auth: dict[str, str]) -> None:
    assert create(client, auth, alias="docs2026").status_code == 201
    for _ in range(3):
        resp = client.get("/docs2026", follow_redirects=False)
        assert resp.status_code == 302
        assert resp.headers["location"] == "https://example.org/articles"
        assert resp.headers["cache-control"] == "no-store"
    item = client.get("/api/v1/links/docs2026/analytics?days=30", headers=auth).json()
    assert item["total_clicks"] == 3
    assert item["last_accessed_at"] is not None
    assert sum(day["clicks"] for day in item["daily"]) == 3
    overall = client.get("/api/v1/analytics", headers=auth).json()
    assert overall["total_links"] == 1
    assert overall["total_clicks"] == 3
    assert overall["top_links"][0] == {"code": "docs2026", "clicks": 3}
    with Session(get_engine()) as db:
        assert db.scalar(select(DailyClick.clicks)) == 3


@pytest.mark.parametrize(
    "target",
    [
        "javascript:alert(1)",
        "file:///etc/passwd",
        "ftp://example.org/a",
        "http://127.0.0.1/admin",
        "http://localhost:8000/secrets",
        "https://user:secret@example.org/",
        "http://192.168.1.2",
        "http://[::1]/",
    ],
)
def test_unsafe_targets_rejected(client: TestClient, auth: dict[str, str], target: str) -> None:
    assert create(client, auth, target_url=target).status_code == 422


@pytest.mark.parametrize("alias", ["api", "docs", "a", "has space", "invalid/"])
def test_bad_aliases_rejected(client: TestClient, auth: dict[str, str], alias: str) -> None:
    assert create(client, auth, alias=alias).status_code == 422


def test_duplicate_alias(client: TestClient, auth: dict[str, str]) -> None:
    assert create(client, auth, alias="custom").status_code == 201
    assert create(client, auth, alias="custom").status_code == 409


def test_generated_collision_retry(client: TestClient, auth: dict[str, str]) -> None:
    assert create(client, auth, alias="abc1234").status_code == 201
    with patch("shortlink.services.generate_code", side_effect=["abc1234", "safe987"]):
        resp = create(client, auth)
    assert resp.status_code == 201
    assert resp.json()["code"] == "safe987"


def test_generated_collision_exhaustion(client: TestClient, auth: dict[str, str]) -> None:
    assert create(client, auth, alias="abc1234").status_code == 201
    with patch("shortlink.services.generate_code", return_value="abc1234"):
        resp = create(client, auth)
    assert resp.status_code == 503


def test_missing_inactive_expired_deleted(client: TestClient, auth: dict[str, str]) -> None:
    assert client.get("/nonexistent", follow_redirects=False).status_code == 404
    assert create(client, auth, alias="disabled").status_code == 201
    assert (
        client.patch("/api/v1/links/disabled", headers=auth, json={"is_active": False}).status_code
        == 200
    )
    assert client.get("/disabled", follow_redirects=False).status_code == 404
    assert (
        client.patch("/api/v1/links/disabled", headers=auth, json={"is_active": True}).status_code
        == 200
    )
    assert client.get("/disabled", follow_redirects=False).status_code == 302
    assert create(client, auth, alias="expired").status_code == 201
    with Session(get_engine()) as db:
        link = db.scalar(select(Link).where(Link.code == "expired"))
        assert link is not None
        link.expires_at = datetime.now(UTC) - timedelta(days=1)
        db.commit()
    assert client.get("/expired", follow_redirects=False).status_code == 404
    assert client.delete("/api/v1/links/disabled", headers=auth).status_code == 204
    assert client.get("/disabled", follow_redirects=False).status_code == 404
    assert client.get("/api/v1/links/disabled", headers=auth).status_code == 404
    assert client.delete("/api/v1/links/disabled", headers=auth).status_code == 404
    assert create(client, auth, alias="disabled").status_code == 409


def test_expiry_input_and_patch(client: TestClient, auth: dict[str, str]) -> None:
    old = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
    future = (datetime.now(UTC) + timedelta(days=7)).isoformat()
    assert create(client, auth, expires_at=old).status_code == 422
    assert create(client, auth, expires_at=future, alias="future").status_code == 201
    assert (
        client.patch("/api/v1/links/future", json={"expires_at": old}, headers=auth).status_code
        == 422
    )
    assert (
        client.patch("/api/v1/links/future", json={"is_active": None}, headers=auth).status_code
        == 422
    )
    assert (
        client.patch("/api/v1/links/future", json={"expires_at": None}, headers=auth).status_code
        == 200
    )


def test_list_pagination_filter(client: TestClient, auth: dict[str, str]) -> None:
    for code in ["alpha", "bravo", "charlie"]:
        assert create(client, auth, alias=code).status_code == 201
    assert (
        client.patch("/api/v1/links/bravo", json={"is_active": False}, headers=auth).status_code
        == 200
    )
    response = client.get("/api/v1/links?limit=2&offset=1", headers=auth)
    assert response.status_code == 200
    assert response.json()["total"] == 3
    assert len(response.json()["items"]) == 2
    assert client.get("/api/v1/links?active=false", headers=auth).json()["total"] == 1
    assert client.get("/api/v1/links?limit=101", headers=auth).status_code == 422
    assert client.get("/api/v1/links?offset=-1", headers=auth).status_code == 422


def test_rate_limit_unit() -> None:
    moment = [100.0]
    limiter = RateLimiter(clock=lambda: moment[0])
    assert limiter.check("admin", 2) == (1, 0)
    assert limiter.check("admin", 2) == (0, 0)
    assert limiter.check("admin", 2)[0] == 0
    moment[0] += 61
    assert limiter.check("admin", 2) == (1, 0)


def test_rate_limit_http(client: TestClient, auth: dict[str, str]) -> None:

    settings = get_settings().model_copy(update={"max_requests_per_minute": 1})
    app.dependency_overrides[get_settings] = lambda: settings
    assert client.get("/api/v1/links", headers=auth).status_code == 200
    denied = client.get("/api/v1/links", headers=auth)
    assert denied.status_code == 429
    assert int(denied.headers["retry-after"]) >= 1


def test_db_integrity_constraint(client: TestClient, auth: dict[str, str]) -> None:
    assert create(client, auth, alias="fixed").status_code == 201
    with Session(get_engine()) as db:
        db.add(Link(code="fixed", target_url="https://example.org"))
        with pytest.raises(IntegrityError):
            db.commit()
        db.rollback()


def test_migrations_applied() -> None:
    with Session(get_engine()) as db:
        version = db.execute(text("SELECT version_num FROM alembic_version")).scalar_one()
    assert version == "0001_initial"


def test_health_handles_database_error(client: TestClient) -> None:
    class BrokenSession:
        def execute(self, _: object) -> None:
            raise RuntimeError("database offline")

    def bad_dependency():
        yield BrokenSession()

    app.dependency_overrides[get_session] = bad_dependency
    response = client.get("/health")
    assert response.status_code == 503
    assert response.json()["detail"] == "Database unavailable"


def test_concurrent_redirects(client: TestClient, auth: dict[str, str]) -> None:
    assert create(client, auth, alias="parallel").status_code == 201
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(
            pool.map(
                lambda _: client.get("/parallel", follow_redirects=False).status_code,
                range(24),
            )
        )
    assert results == [302] * 24
    stats = client.get("/api/v1/links/parallel/analytics", headers=auth).json()
    assert stats["total_clicks"] == 24
    assert sum(record["clicks"] for record in stats["daily"]) == 24
