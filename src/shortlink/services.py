"""Business rules for code allocation and lifecycle, separate from database queries."""

import secrets
import string
from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shortlink import repositories
from shortlink.models import Link
from shortlink.schemas import LinkCreate, LinkRead, LinkUpdate

ALPHABET = string.ascii_letters + string.digits
MAX_CODE_ATTEMPTS = 6


def generate_code(length: int = 7) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


def get_link(session: Session, code: str) -> Link:
    link = repositories.find_link(session, code)
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
        try:
            return repositories.persist_new(session, link)
        except IntegrityError:
            session.rollback()
            if payload.alias:
                raise HTTPException(status_code=409, detail="Alias already exists") from None
    raise HTTPException(status_code=503, detail="Could not allocate a unique code")


def update_link(session: Session, link: Link, payload: LinkUpdate) -> Link:
    changes = payload.model_dump(exclude_unset=True)
    for name, value in changes.items():
        setattr(link, name, value)
    return repositories.persist_existing(session, link)


def delete_link(session: Session, link: Link) -> None:
    repositories.soft_delete(session, link, datetime.now(UTC))


def record_redirect(session: Session, code: str) -> str:
    target = repositories.increment_and_track(session, code, datetime.now(UTC))
    if target is None:
        raise HTTPException(status_code=404, detail="Link not found")
    return target


def list_links(
    session: Session, limit: int, offset: int, active: bool | None
) -> tuple[list[Link], int]:
    return repositories.page(session, limit, offset, active)
