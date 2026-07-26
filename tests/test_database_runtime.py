from __future__ import annotations

from app.config import Settings
from app.database import build_engine_options, normalize_database_url
from app.observability.database import InstrumentedAsyncQueuePool, normalized_query_shape
from app.version import APP_VERSION


def settings(**overrides) -> Settings:
    values = {
        "bot_token": "123456:test-token",
        "webhook_path_secret": "path-secret",
        "webhook_header_secret": "header-secret",
    }
    values.update(overrides)
    return Settings(**values)


def test_postgres_runtime_has_bounded_pool_and_statement_timeout() -> None:
    current = settings(
        db_pool_size=7,
        db_max_overflow=2,
        db_pool_timeout_seconds=4,
        db_pool_recycle_seconds=600,
        db_statement_timeout_ms=9000,
        db_disable_prepared_statements=True,
        build_sha="abc123",
    )
    options = build_engine_options("postgresql+asyncpg://example/db", current)
    assert options["poolclass"] is InstrumentedAsyncQueuePool
    assert options["pool_size"] == 7
    assert options["max_overflow"] == 2
    assert options["pool_timeout"] == 4
    assert options["pool_recycle"] == 600
    assert options["connect_args"]["server_settings"] == {
        "application_name": f"chatpulse/{APP_VERSION}",
        "statement_timeout": "9000",
    }
    assert options["connect_args"]["statement_cache_size"] == 0


def test_sqlite_does_not_receive_postgres_pool_options() -> None:
    options = build_engine_options("sqlite+aiosqlite:///:memory:", settings())
    assert options == {"connect_args": {"timeout": 30}}


def test_slow_query_shape_never_contains_parameters() -> None:
    operation, tables = normalized_query_shape(
        "SELECT * FROM group_members WHERE telegram_user_id = 123 AND username = 'secret'"
    )
    assert operation == "SELECT"
    assert tables == ("group_members",)


def test_plain_postgres_url_is_normalized() -> None:
    assert normalize_database_url("postgresql://host/db") == "postgresql+asyncpg://host/db"
