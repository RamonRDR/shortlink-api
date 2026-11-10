"""HTTP surface. Administration requires X-API-Key; only redirects are public."""

from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from shortlink.analytics import link_analytics, summary_analytics
from shortlink.config import Settings, get_settings
from shortlink.db import get_session
from shortlink.rate_limit import rate_limited_admin
from shortlink.schemas import LinkCreate, LinkPage, LinkRead, LinkStats, LinkUpdate, SummaryStats
from shortlink.services import (
    create_link,
    delete_link,
    get_link,
    list_links,
    record_redirect,
    serialize_link,
    update_link,
)

app = FastAPI(title="ShortLink API", version="0.1.0")
Db = Annotated[Session, Depends(get_session)]
Config = Annotated[Settings, Depends(get_settings)]
Admin = Annotated[str, Depends(rate_limited_admin)]


@app.get("/health", tags=["health"])
def health(db: Db) -> dict[str, str]:
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        raise HTTPException(status_code=503, detail="Database unavailable") from None
    return {"status": "ok"}


@app.post(
    "/api/v1/links", response_model=LinkRead, status_code=status.HTTP_201_CREATED, tags=["links"]
)
def create(payload: LinkCreate, db: Db, settings: Config, _: Admin) -> LinkRead:
    return serialize_link(create_link(db, payload), str(settings.base_url))


@app.get("/api/v1/links", response_model=LinkPage, tags=["links"])
def list_all(
    db: Db,
    settings: Config,
    _: Admin,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    offset: Annotated[int, Query(ge=0)] = 0,
    active: bool | None = None,
) -> LinkPage:
    links, total = list_links(db, limit, offset, active)
    return LinkPage(
        items=[serialize_link(link, str(settings.base_url)) for link in links],
        total=total,
        limit=limit,
        offset=offset,
    )


@app.get("/api/v1/links/{code}", response_model=LinkRead, tags=["links"])
def detail(code: str, db: Db, settings: Config, _: Admin) -> LinkRead:
    return serialize_link(get_link(db, code), str(settings.base_url))


@app.patch("/api/v1/links/{code}", response_model=LinkRead, tags=["links"])
def modify(code: str, payload: LinkUpdate, db: Db, settings: Config, _: Admin) -> LinkRead:
    link = get_link(db, code)
    return serialize_link(update_link(db, link, payload), str(settings.base_url))


@app.delete("/api/v1/links/{code}", status_code=status.HTTP_204_NO_CONTENT, tags=["links"])
def remove(code: str, db: Db, _: Admin) -> Response:
    delete_link(db, get_link(db, code))
    return Response(status_code=204)


@app.get("/api/v1/links/{code}/analytics", response_model=LinkStats, tags=["analytics"])
def link_stats(
    code: str,
    db: Db,
    _: Admin,
    days: Annotated[int, Query(ge=1, le=365)] = 30,
) -> LinkStats:
    return link_analytics(db, get_link(db, code), days)


@app.get("/api/v1/analytics", response_model=SummaryStats, tags=["analytics"])
def all_stats(
    db: Db,
    _: Admin,
    top: Annotated[int, Query(ge=1, le=100)] = 10,
) -> SummaryStats:
    return summary_analytics(db, top)


@app.get("/{code}", include_in_schema=True, tags=["redirects"])
def redirect(code: str, db: Db) -> RedirectResponse:
    if not (4 <= len(code) <= 32 and all(c.isalnum() or c in "_-" for c in code)):
        raise HTTPException(status_code=404, detail="Link not found")
    target = record_redirect(db, code)
    return RedirectResponse(url=target, status_code=302, headers={"Cache-Control": "no-store"})
