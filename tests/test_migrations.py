from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrades_empty_database_to_head(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.db"
    database_url = f"sqlite:///{database_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", database_url)

    command.upgrade(config, "head")

    inspector = inspect(create_engine(database_url))
    assert "users" in inspector.get_table_names()
    assert "processed_updates" in inspector.get_table_names()
    columns = {column["name"] for column in inspector.get_columns("processed_updates")}
    assert {
        "update_id",
        "update_type",
        "status",
        "attempts",
        "started_at",
        "lease_expires_at",
        "completed_at",
        "last_error",
    } <= columns
