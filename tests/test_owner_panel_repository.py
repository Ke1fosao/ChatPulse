from datetime import UTC, datetime, timedelta

import pytest

from app.database import Database
from app.models import User
from app.repositories.owner import OwnerRepository
from app.repositories.owner_panel import OwnerPanelRepository


@pytest.fixture
async def repositories(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'owner-panel.db'}")
    await database.create_schema()
    async with database.session_factory() as session, session.begin():
        session.add_all(
            [
                User(telegram_id=101, username="veheblya", first_name="Dmytro"),
                User(telegram_id=202, username="client", first_name="Client"),
            ]
        )
    owner_repository = OwnerRepository(database.session_factory)
    await owner_repository.claim_owner(101, "veheblya")
    yield OwnerPanelRepository(database.session_factory)
    await database.dispose()


@pytest.mark.asyncio
async def test_owner_can_grant_permanent_vip_and_action_is_audited(repositories) -> None:
    now = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)

    grant = await repositories.grant_vip(
        owner_user_id=101,
        target_user_id=202,
        expires_at=None,
        reason="Партнерський VIP",
        now=now,
    )

    assert grant["is_active"] is True
    assert grant["expires_at"] is None
    assert await repositories.is_active_vip(202, now=now) is True
    audit = await repositories.list_audit(limit=10)
    assert audit[0]["action"] == "vip.granted"
    assert audit[0]["target_id"] == "202"


@pytest.mark.asyncio
async def test_timed_vip_expires_automatically(repositories) -> None:
    now = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)
    expires_at = now + timedelta(days=7)
    await repositories.grant_vip(
        owner_user_id=101,
        target_user_id=202,
        expires_at=expires_at,
        reason="Тест на тиждень",
        now=now,
    )

    assert await repositories.is_active_vip(202, now=expires_at - timedelta(seconds=1)) is True
    assert await repositories.is_active_vip(202, now=expires_at) is False


@pytest.mark.asyncio
async def test_owner_cannot_be_targeted_by_vip_mutations(repositories) -> None:
    with pytest.raises(ValueError, match="owner"):
        await repositories.grant_vip(
            owner_user_id=101,
            target_user_id=101,
            expires_at=None,
            reason="Неприпустимо",
        )


@pytest.mark.asyncio
async def test_owner_can_revoke_vip_and_history_is_preserved(repositories) -> None:
    await repositories.grant_vip(
        owner_user_id=101,
        target_user_id=202,
        expires_at=None,
        reason="Подарунок",
    )

    revoked = await repositories.revoke_vip(
        owner_user_id=101,
        target_user_id=202,
        reason="Завершення програми",
    )

    assert revoked["is_active"] is False
    assert await repositories.is_active_vip(202) is False
    audit = await repositories.list_audit(limit=10)
    assert [item["action"] for item in audit[:2]] == ["vip.revoked", "vip.granted"]
