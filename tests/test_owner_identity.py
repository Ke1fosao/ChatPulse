import pytest

from app.database import Database
from app.repositories.owner import OwnerClaimResult, OwnerRepository


@pytest.mark.asyncio
async def test_username_alone_cannot_claim_owner(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'owner.db'}")
    await database.create_schema()
    repository = OwnerRepository(database.session_factory, allowed_owner_id=123456)

    result = await repository.claim_owner(999999, "veheblya")

    assert result is OwnerClaimResult.ID_MISMATCH
    assert not await repository.is_owner(999999)
    await database.dispose()


@pytest.mark.asyncio
async def test_configured_telegram_id_claims_owner_regardless_of_username(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'owner-ok.db'}")
    await database.create_schema()
    repository = OwnerRepository(database.session_factory, allowed_owner_id=123456)

    result = await repository.claim_owner(123456, "renamed_account")

    assert result is OwnerClaimResult.CLAIMED
    assert await repository.is_owner(123456)
    await database.dispose()
