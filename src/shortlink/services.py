"""Business operations with database-enforced uniqueness and atomic click counts."""

import secrets
import string
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shortlink.models import DailyClick, Link
from shortlink.schemas import LinkCreate, LinkRead, LinkUpdate

ALPHABET = string.ascii_letters + string.digits
MAX_CODE_ATTEMPTS = 6


def generate_code(length: int = 7) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def get_link(session: Session, code: str) -> Link:
    link = session.scalar(select(Link).where(Link.code == code, Link.deleted_at.is_(None)))
    if link is None:
        raise HTTPException(status_code=404, detail="Link not found")
    return link


def serialize_link(link: Link, base_url: str) -> LinkRead:
    return LinkRead(
        code=link.code,
        target_url=link.target_url,
        short_url=f"{base_url.rstrip('/')}/{link.code}",
        is_active=link.is_active,
        expires_at=link.expires_at,
        created_at=link.created_at,
        updated_at=link.updated_at,
        click_count=link.click_count,
        last_accessed_at=link.last_accessed_at,
    )


def create_link(session: Session, payload: LinkCreate) -> Link:
    attempts = 1 if payload.alias else MAX_CODE_ATTEMPTS
    for _ in range(attempts):
        link = Link(
            code=payload.alias or generate_code(),
            target_url=str(payload.target_url),
            expires_at=payload.expires_at,
        )
        session.add(link)
        try:
            session.commit()
            session.refresh(link)
            return link
        except IntegrityError:
            session.rollback()
            if payload.alias:
                raise HTTPException(status_code=409, detail="Alias already exists") from None
    raise HTTPException(status_code=503, detail="Could not allocate a unique code")


def update_link(session: Session, link: Link, payload: LinkUpdate) -> Link:
    changes = payload.model_dump(exclude_unset=True)
    for name, value in changes.items():
        setattr(link, name, value)
    session.commit()
    session.refresh(link)
    return link


def delete_link(session: Session, link: Link) -> None:
    link.deleted_at = datetime.now(UTC)
    link.is_active = False
    session.commit()


def record_redirect(session: Session, code: str) -> str:
    """Lock the link row through UPDATE, then atomically upsert the daily counter."""
    now = datetime.now(UTC)
    stmt = (
        update(Link)
        .where(
            Link.code == code,
            Link.deleted_at.is_(None),
            Link.is_active.is_(True),
            (Link.expires_at.is_(None) | (Link.expires_at > now)),
        )
        .values(click_count=Link.click_count + 1, last_accessed_at=now)
        .returning(Link.id, Link.target_url)
    )
    result = session.execute(stmt).one_or_none()
    if result is None:
        session.rollback()
        raise HTTPException(status_code=404, detail="Link not found")
    link_id, target_url = result
    day = now.date()
    statement = insert(DailyClick).values(link_id=link_id, day=day, clicks=1)
    statement = statement.on_conflict_do_update(
        constraint="uq_daily_clicks_link_day",
        set_={"clicks": DailyClick.clicks + 1},
    )
    session.execute(statement)
    session.commit()
    return str(target_url)


def list_links(
    session: Session, limit: int, offset: int, active: bool | None
) -> tuple[list[Link], int]:
    query = select(Link).where(Link.deleted_at.is_(None))
    if active is not None:
        query = query.where(Link.is_active == active)
    total = session.scalar(select(func.count()).select_from(query.subquery())) or 0
    items = list(
        session.scalars(
            query.order_by(Link.created_at.desc(), Link.id.desc()).limit(limit).offset(offset)
        )
    )
    return items, total
