"""Privacy-preserving aggregated analytics (UTC day buckets, no IP tracking)."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import desc, func, select
from sqlalchemy.orm import Session

from shortlink.models import DailyClick, Link
from shortlink.schemas import DailyStat, LinkStats, SummaryStats, TopLink


def link_analytics(session: Session, link: Link, days: int) -> LinkStats:
    since = datetime.now(UTC).date() - timedelta(days=days - 1)
    rows = session.execute(
        select(DailyClick.day, DailyClick.clicks)
        .where(DailyClick.link_id == link.id, DailyClick.day >= since)
        .order_by(DailyClick.day)
    ).all()
    return LinkStats(
        code=link.code,
        total_clicks=link.click_count,
        last_accessed_at=link.last_accessed_at,
        daily=[DailyStat(day=day, clicks=clicks) for day, clicks in rows],
    )


def summary_analytics(session: Session, top: int) -> SummaryStats:
    totals = session.execute(
        select(func.count(Link.id), func.coalesce(func.sum(Link.click_count), 0)).where(
            Link.deleted_at.is_(None)
        )
    ).one()
    rows = session.execute(
        select(Link.code, Link.click_count)
        .where(Link.deleted_at.is_(None))
        .order_by(desc(Link.click_count), Link.code)
        .limit(top)
    ).all()
    return SummaryStats(
        total_links=totals[0],
        total_clicks=totals[1],
        top_links=[TopLink(code=code, clicks=clicks) for code, clicks in rows],
    )
