"""Expand daily aggregate IDs and their PostgreSQL sequence to 64 bits.

Revision ID: 0002_daily_id_bigint
Revises: 0001_initial
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_daily_id_bigint"
down_revision: str | None = "0001_initial"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column(
        "daily_clicks",
        "id",
        existing_type=sa.Integer(),
        type_=sa.BigInteger(),
        existing_nullable=False,
    )
    op.execute("ALTER SEQUENCE daily_clicks_id_seq AS bigint")


def downgrade() -> None:
    op.execute("ALTER SEQUENCE daily_clicks_id_seq AS integer")
    op.alter_column(
        "daily_clicks",
        "id",
        existing_type=sa.BigInteger(),
        type_=sa.Integer(),
        existing_nullable=False,
    )
