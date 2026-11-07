"""Create links and daily_clicks.

Revision ID: 0001_initial
Revises:
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "links",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("target_url", sa.String(length=2048), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("click_count", sa.BigInteger(), server_default="0", nullable=False),
        sa.Column("last_accessed_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("click_count >= 0", name="ck_links_click_count_nonnegative"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_links_created_at", "links", ["created_at"])
    op.create_index("ix_links_active_expires", "links", ["is_active", "expires_at"])
    op.create_table(
        "daily_clicks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("link_id", sa.BigInteger(), nullable=False),
        sa.Column("day", sa.Date(), nullable=False),
        sa.Column("clicks", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("clicks > 0", name="ck_daily_clicks_positive"),
        sa.ForeignKeyConstraint(["link_id"], ["links.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("link_id", "day", name="uq_daily_clicks_link_day"),
    )
    op.create_index("ix_daily_clicks_day", "daily_clicks", ["day"])


def downgrade() -> None:
    op.drop_index("ix_daily_clicks_day", table_name="daily_clicks")
    op.drop_table("daily_clicks")
    op.drop_index("ix_links_active_expires", table_name="links")
    op.drop_index("ix_links_created_at", table_name="links")
    op.drop_table("links")
