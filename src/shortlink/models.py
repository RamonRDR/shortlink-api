"""Relational schema for short links and private aggregate analytics."""

from datetime import date, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from shortlink.db import Base


class Link(Base):
    __tablename__ = "links"
    __table_args__ = (
        CheckConstraint("click_count >= 0", name="ck_links_click_count_nonnegative"),
        Index("ix_links_created_at", "created_at"),
        Index("ix_links_active_expires", "is_active", "expires_at"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    code: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    target_url: Mapped[str] = mapped_column(String(2048), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    click_count: Mapped[int] = mapped_column(
        BigInteger, nullable=False, server_default="0", default=0
    )
    last_accessed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    daily_clicks: Mapped[list["DailyClick"]] = relationship(
        back_populates="link", cascade="all, delete-orphan"
    )


class DailyClick(Base):
    __tablename__ = "daily_clicks"
    __table_args__ = (
        UniqueConstraint("link_id", "day", name="uq_daily_clicks_link_day"),
        CheckConstraint("clicks > 0", name="ck_daily_clicks_positive"),
        Index("ix_daily_clicks_day", "day"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    link_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("links.id", ondelete="CASCADE"), nullable=False
    )
    day: Mapped[date] = mapped_column(Date, nullable=False)
    clicks: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    link: Mapped[Link] = relationship(back_populates="daily_clicks")
