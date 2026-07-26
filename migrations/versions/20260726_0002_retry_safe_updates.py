"""Add retry-safe Telegram update state.

Revision ID: 20260726_0002
Revises: 20260726_0001
Create Date: 2026-07-26
"""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa

revision: str = "20260726_0002"
down_revision: str | None = "20260726_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_names(table_name: str) -> set[str]:
    return {column["name"] for column in sa.inspect(op.get_bind()).get_columns(table_name)}


def _index_names(table_name: str) -> set[str]:
    return {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}


def upgrade() -> None:
    columns = _column_names("processed_updates")
    added_started_at = "started_at" not in columns
    with op.batch_alter_table("processed_updates") as batch:
        if "status" not in columns:
            batch.add_column(
                sa.Column(
                    "status",
                    sa.String(length=16),
                    nullable=False,
                    server_default="completed",
                )
            )
        if "attempts" not in columns:
            batch.add_column(
                sa.Column("attempts", sa.Integer(), nullable=False, server_default="1")
            )
        if added_started_at:
            batch.add_column(sa.Column("started_at", sa.DateTime(timezone=True), nullable=True))
        if "lease_expires_at" not in columns:
            batch.add_column(sa.Column("lease_expires_at", sa.DateTime(timezone=True)))
        if "completed_at" not in columns:
            batch.add_column(sa.Column("completed_at", sa.DateTime(timezone=True)))
        if "last_error" not in columns:
            batch.add_column(sa.Column("last_error", sa.String(length=128)))

    if added_started_at:
        op.execute(
            sa.text(
                "UPDATE processed_updates SET started_at = processed_at "
                "WHERE started_at IS NULL"
            )
        )
        with op.batch_alter_table("processed_updates") as batch:
            batch.alter_column("started_at", existing_type=sa.DateTime(timezone=True), nullable=False)

    update_indexes = _index_names("processed_updates")
    if "ix_processed_updates_status_lease" not in update_indexes:
        op.create_index(
            "ix_processed_updates_status_lease",
            "processed_updates",
            ["status", "lease_expires_at"],
        )

    daily_indexes = _index_names("daily_activity")
    if "ix_daily_activity_chat_date" not in daily_indexes:
        op.create_index(
            "ix_daily_activity_chat_date",
            "daily_activity",
            ["telegram_chat_id", "activity_date"],
        )


def downgrade() -> None:
    if "ix_processed_updates_status_lease" in _index_names("processed_updates"):
        op.drop_index("ix_processed_updates_status_lease", table_name="processed_updates")
    with op.batch_alter_table("processed_updates") as batch:
        for column_name in (
            "last_error",
            "completed_at",
            "lease_expires_at",
            "started_at",
            "attempts",
            "status",
        ):
            if column_name in _column_names("processed_updates"):
                batch.drop_column(column_name)
