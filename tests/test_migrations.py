from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect


def test_alembic_upgrades_empty_database_to_head(tmp_path: Path) -> None:
    database_path = tmp_path / "migration.db"
    migration_url = f"sqlite+aiosqlite:///{database_path}"
    inspection_url = f"sqlite:///{database_path}"
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", migration_url)

    command.upgrade(config, "head")

    inspector = inspect(create_engine(inspection_url))
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


def test_alembic_upgrades_legacy_processed_updates_table(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.db"
    inspection_url = f"sqlite:///{database_path}"
    engine = create_engine(inspection_url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE processed_updates ("
            "update_id BIGINT PRIMARY KEY, "
            "update_type VARCHAR(64) NOT NULL, "
            "processed_at DATETIME NOT NULL"
            ")"
        )
        connection.exec_driver_sql(
            "INSERT INTO processed_updates (update_id, update_type, processed_at) "
            "VALUES (1, 'message', '2026-07-26 10:00:00')"
        )
    engine.dispose()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{database_path}")
    command.upgrade(config, "head")
    inspector = inspect(create_engine(inspection_url))
    columns = {column["name"] for column in inspector.get_columns("processed_updates")}
    assert {"status", "attempts", "lease_expires_at", "completed_at", "last_error"} <= columns
