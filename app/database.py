from __future__ import annotations

from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

import app.achievement_models  # noqa: F401
import app.billing_models  # noqa: F401
import app.engagement_models  # noqa: F401
import app.groups_v2_models  # noqa: F401
import app.owner_revenue_models  # noqa: F401
import app.user_control_models  # noqa: F401
import app.vip_product_models  # noqa: F401
from app.models import Base
from app.observability.database import install_query_instrumentation, postgresql_engine_options


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


def build_engine_options(normalized_url: str, settings=None) -> dict[str, Any]:
    if normalized_url.startswith("sqlite"):
        return {"connect_args": {"timeout": 30}}
    if settings is None:
        return {"pool_pre_ping": True}
    return postgresql_engine_options(settings)


class Database:
    def __init__(self, database_url: str, *, settings=None, metrics=None) -> None:
        self.normalized_url = normalize_database_url(database_url)
        self.is_sqlite = self.normalized_url.startswith("sqlite")
        self.engine = create_async_engine(
            self.normalized_url,
            **build_engine_options(self.normalized_url, settings),
        )
        if settings is not None:
            install_query_instrumentation(
                self.engine,
                slow_query_ms=settings.db_slow_query_ms,
                metrics=metrics,
            )
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def create_schema(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def ping(self) -> None:
        async with self.engine.connect() as connection:
            await connection.execute(text("SELECT 1"))

    async def migration_revision(self) -> str | None:
        if self.is_sqlite:
            return None
        async with self.engine.connect() as connection:
            result = await connection.execute(text("SELECT version_num FROM alembic_version"))
            revision = result.scalar_one_or_none()
            return str(revision) if revision else None

    async def dispose(self) -> None:
        await self.engine.dispose()
