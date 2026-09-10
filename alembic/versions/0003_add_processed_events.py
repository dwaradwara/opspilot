"""add processed events

Revision ID: 0003
Revises: 0002
Create Date: 2026-09-10
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "processed_events",
        sa.Column("event_id", sa.UUID(), nullable=False),
        sa.Column("consumer_name", sa.String(length=100), nullable=False),
        sa.Column("event_type", sa.String(length=100), nullable=False),
        sa.Column(
            "processed_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("event_id", "consumer_name"),
    )

    op.create_index(
        op.f("ix_processed_events_event_type"),
        "processed_events",
        ["event_type"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_processed_events_event_type"),
        table_name="processed_events",
    )

    op.drop_table("processed_events")
