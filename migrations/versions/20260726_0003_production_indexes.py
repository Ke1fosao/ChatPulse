"""Add audited production query indexes.

Revision ID: 20260726_0003
Revises: 20260726_0002
Create Date: 2026-07-26
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260726_0003"
down_revision: str | None = "20260726_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_INDEXES: tuple[tuple[str, str, tuple[str, ...]], ...] = (
    ("ix_users_last_activity", "users", ("last_activity_at",)),
    (
        "ix_chat_groups_report_due",
        "chat_groups",
        (
            "is_active",
            "is_paused",
            "weekly_reports_enabled",
            "report_weekday",
            "report_hour",
            "report_minute",
        ),
    ),
    (
        "ix_group_members_user_seen",
        "group_members",
        ("telegram_user_id", "last_seen_at"),
    ),
    (
        "ix_group_members_chat_xp",
        "group_members",
        ("telegram_chat_id", "xp_total"),
    ),
    (
        "ix_engagement_notifications_status_claimed",
        "engagement_notifications",
        ("status", "claimed_at"),
    ),
    (
        "ix_vip_invoice_status_created",
        "vip_invoice_intents",
        ("status", "created_at"),
    ),
)


def _index_names(table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    for name, table, columns in _INDEXES:
        if name not in _index_names(table):
            op.create_index(name, table, list(columns))


def downgrade() -> None:
    for name, table, _ in reversed(_INDEXES):
        if name in _index_names(table):
            op.drop_index(name, table_name=table)
