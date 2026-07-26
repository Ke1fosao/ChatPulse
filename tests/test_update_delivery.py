from datetime import UTC, datetime, timedelta

import pytest

from app.database import Database
from app.repositories.activity import ActivityRepository, UpdateClaim


@pytest.mark.asyncio
async def test_update_is_completed_only_after_success(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'updates.db'}")
    await database.create_schema()
    repository = ActivityRepository(database.session_factory)
    now = datetime(2026, 7, 26, 10, 0, tzinfo=UTC)

    assert await repository.begin_update(1001, "message", now=now) is UpdateClaim.PROCESS
    await repository.complete_update(1001, now=now + timedelta(seconds=1))
    assert (
        await repository.begin_update(1001, "message", now=now + timedelta(seconds=2))
        is UpdateClaim.COMPLETED_DUPLICATE
    )

    await database.dispose()


@pytest.mark.asyncio
async def test_failed_update_can_be_retried(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'retry.db'}")
    await database.create_schema()
    repository = ActivityRepository(database.session_factory)
    now = datetime(2026, 7, 26, 10, 0, tzinfo=UTC)

    assert await repository.begin_update(1002, "message", now=now) is UpdateClaim.PROCESS
    await repository.fail_update(1002, "RuntimeError", now=now + timedelta(seconds=1))
    assert (
        await repository.begin_update(1002, "message", now=now + timedelta(seconds=2))
        is UpdateClaim.PROCESS
    )

    await database.dispose()


@pytest.mark.asyncio
async def test_active_lease_blocks_parallel_processing_but_expired_lease_retries(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'lease.db'}")
    await database.create_schema()
    repository = ActivityRepository(database.session_factory)
    now = datetime(2026, 7, 26, 10, 0, tzinfo=UTC)

    assert await repository.begin_update(1003, "message", now=now) is UpdateClaim.PROCESS
    assert (
        await repository.begin_update(1003, "message", now=now + timedelta(seconds=30))
        is UpdateClaim.IN_PROGRESS
    )
    assert (
        await repository.begin_update(1003, "message", now=now + timedelta(minutes=6))
        is UpdateClaim.PROCESS
    )

    await database.dispose()
