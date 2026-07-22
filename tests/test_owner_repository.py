from datetime import UTC, datetime

import pytest

from app.database import Database
from app.repositories.owner import OwnerClaimResult, OwnerRepository


@pytest.fixture
async def owner_repository(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'owner.db'}")
    await database.create_schema()
    yield OwnerRepository(database.session_factory)
    await database.dispose()


@pytest.mark.asyncio
async def test_veheblya_can_claim_owner_once(owner_repository) -> None:
    claimed_at = datetime(2026, 7, 22, 9, 0, tzinfo=UTC)

    result = await owner_repository.claim_owner(
        telegram_user_id=101,
        username="@Veheblya",
        claimed_at=claimed_at,
    )

    assert result is OwnerClaimResult.CLAIMED
    assert await owner_repository.is_owner(101) is True
    assert await owner_repository.is_owner(202) is False


@pytest.mark.asyncio
async def test_wrong_username_cannot_claim_owner(owner_repository) -> None:
    result = await owner_repository.claim_owner(
        telegram_user_id=101,
        username="someone_else",
    )

    assert result is OwnerClaimResult.USERNAME_MISMATCH
    assert await owner_repository.is_owner(101) is False


@pytest.mark.asyncio
async def test_same_owner_claim_is_idempotent(owner_repository) -> None:
    first = await owner_repository.claim_owner(101, "veheblya")
    second = await owner_repository.claim_owner(101, "veheblya")

    assert first is OwnerClaimResult.CLAIMED
    assert second is OwnerClaimResult.ALREADY_OWNER


@pytest.mark.asyncio
async def test_other_account_cannot_replace_claimed_owner(owner_repository) -> None:
    await owner_repository.claim_owner(101, "veheblya")

    result = await owner_repository.claim_owner(202, "veheblya")

    assert result is OwnerClaimResult.CLAIMED_BY_OTHER
    assert await owner_repository.is_owner(101) is True
    assert await owner_repository.is_owner(202) is False
