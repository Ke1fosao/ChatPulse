from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import Base


def normalize_database_url(database_url: str) -> str:
    if database_url.startswith("postgresql://"):
        return database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
    return database_url


class Database:
    def __init__(self, database_url: str) -> None:
        normalized_url = normalize_database_url(database_url)
        engine_kwargs: dict = {"pool_pre_ping": True}
        if normalized_url.startswith("sqlite"):
            # Cloud Run may deliver webhook requests close together. A longer
            # busy timeout prevents short-lived SQLite write locks from failing.
            engine_kwargs["connect_args"] = {"timeout": 30}

        self.engine = create_async_engine(normalized_url, **engine_kwargs)
        self.session_factory = async_sessionmaker(
            bind=self.engine,
            class_=AsyncSession,
            expire_on_commit=False,
        )

    async def create_schema(self) -> None:
        async with self.engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    async def dispose(self) -> None:
        await self.engine.dispose()
