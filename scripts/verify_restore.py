from __future__ import annotations

import argparse
import asyncio
import os
from urllib.parse import urlsplit

from sqlalchemy import inspect, text
from sqlalchemy.ext.asyncio import create_async_engine

from app.database import normalize_database_url

CRITICAL_TABLES = {
    "users",
    "chat_groups",
    "group_members",
    "processed_updates",
    "vip_payments",
    "alembic_version",
}


def _validate_target(database_url: str) -> None:
    if os.getenv("ALLOW_RESTORE_VERIFICATION") != "1":
        raise RuntimeError("Set ALLOW_RESTORE_VERIFICATION=1 for an explicit restored target")
    target = urlsplit(database_url.replace("+asyncpg", ""))
    combined = f"{target.hostname or ''}/{target.path}".casefold()
    if any(marker in combined for marker in ("production", "/prod", "primary")):
        raise RuntimeError("Restore verification refuses production-like targets")


async def verify(database_url: str) -> None:
    _validate_target(database_url)
    engine = create_async_engine(normalize_database_url(database_url), pool_pre_ping=True)
    try:
        async with engine.connect() as connection:
            tables = set(await connection.run_sync(lambda sync: inspect(sync).get_table_names()))
            missing = sorted(CRITICAL_TABLES - tables)
            if missing:
                raise RuntimeError(f"Missing critical tables: {', '.join(missing)}")
            revision = (await connection.execute(text("SELECT version_num FROM alembic_version"))).scalar()
            if not revision:
                raise RuntimeError("Alembic revision is missing")
            duplicates = (
                await connection.execute(
                    text(
                        "SELECT COUNT(*) FROM ("
                        "SELECT telegram_payment_charge_id FROM vip_payments "
                        "GROUP BY telegram_payment_charge_id HAVING COUNT(*) > 1"
                        ") AS duplicate_charges"
                    )
                )
            ).scalar_one()
            if duplicates:
                raise RuntimeError("Duplicate Telegram payment charge IDs detected")
            for table in sorted(CRITICAL_TABLES - {"alembic_version"}):
                await connection.execute(text(f'SELECT COUNT(*) FROM "{table}"'))
            print(f"restore_revision={revision}")
            print("restore_verification_ok=true")
    finally:
        await engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--database-url", required=True)
    args = parser.parse_args()
    asyncio.run(verify(args.database_url))


if __name__ == "__main__":
    main()
