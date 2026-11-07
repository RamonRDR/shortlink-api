"""Focused SQLAlchemy data-access functions, isolated from HTTP and business rules."""

from datetime import datetime

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from shortlink.models import DailyClick, Link


def find_link(session: Session, code: str) -> Link | None:
    return session.scalar(select(Link).where(Link.code == code, Link.deleted_at.is_(None)))


def persist_new(session: Session, link: Link) -> Link:
    session.add(link)
    session.commit()
    session.refresh(link)
    return link


def persist_existing(session: Session, link: Link) -> Link:
    session.commit()
    session.refresh(link)
    return link


def soft_delete(session: Session, link: Link, now: datetime) -> None:
    link.deleted_at = now
    link.is_active = False
    session.commit()


def increment_and_track(session: Session, code: str, now: datetime) -> str | None:
    """Atomic increment + UPSERT in one transaction, including concurrent calls."""
    statement = (
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
    result = session.execute(statement).one_or_none()
    if result is None:
        session.rollback()
        return None
    link_id, target_url = result
    insert_stmt = insert(DailyClick).values(link_id=link_id, day=now.date(), clicks=1)
    insert_stmt = insert_stmt.on_conflict_do_update(
        constraint="uq_daily_clicks_link_day",
        set_={"clicks": DailyClick.clicks + 1},
    )
    session.execute(insert_stmt)
    session.commit()
    return str(target_url)


def page(session: Session, limit: int, offset: int, active: bool | None) -> tuple[list[Link], int]:
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
