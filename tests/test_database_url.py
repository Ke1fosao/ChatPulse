from app.database import normalize_database_url


def test_postgresql_url_uses_asyncpg_driver() -> None:
    assert normalize_database_url("postgresql://user:pass@host/db") == (
        "postgresql+asyncpg://user:pass@host/db"
    )


def test_existing_async_and_sqlite_urls_are_unchanged() -> None:
    assert normalize_database_url("postgresql+asyncpg://user:pass@host/db") == (
        "postgresql+asyncpg://user:pass@host/db"
    )
    assert normalize_database_url("sqlite+aiosqlite:///./chatpulse.db") == (
        "sqlite+aiosqlite:///./chatpulse.db"
    )
