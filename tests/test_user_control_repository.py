from datetime import UTC, datetime

import pytest
from sqlalchemy import select

from app.database import Database
from app.models import OwnerAuditLog, User
from app.repositories.owner import OwnerRepository
from app.repositories.user_control import UserControlRepository
from app.services.admin_access import AdminActor, ROLE_PERMISSIONS
from app.user_control_models import BlockedAccessEvent, UserAdminTag, UserXpAdjustment


async def seed_users(database: Database) -> tuple[AdminActor, UserControlRepository]:
    async with database.session_factory() as session, session.begin():
        session.add_all(
            [
                User(telegram_id=101, username="owner", first_name="Owner"),
                User(
                    telegram_id=202,
                    username="member",
                    first_name="Member",
                    global_xp_total=100,
                    global_level=2,
                ),
            ]
        )
    await OwnerRepository(database.session_factory).claim_owner(101, "owner")
    actor = AdminActor(
        telegram_user_id=101,
        role="owner",
        permissions=ROLE_PERMISSIONS["owner"],
    )
    return actor, UserControlRepository(database.session_factory)


@pytest.mark.asyncio
async def test_block_and_unblock_are_enforced_and_audited(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'user-control.db'}")
    await database.create_schema()
    actor, repository = await seed_users(database)

    blocked = await repository.block_user(actor, 202, "Порушення правил")
    assert blocked["is_blocked"] is True
    assert await repository.is_blocked(202) is True
    assert (await repository.get_block_info(202))["reason"] == "Порушення правил"

    unblocked = await repository.unblock_user(actor, 202, "Апеляцію прийнято")
    assert unblocked["is_blocked"] is False
    assert await repository.is_blocked(202) is False

    async with database.session_factory() as session:
        actions = list(
            await session.scalars(
                select(OwnerAuditLog.action).order_by(OwnerAuditLog.id.asc())
            )
        )
    assert actions[-2:] == ["user.blocked", "user.unblocked"]
    await database.dispose()


@pytest.mark.asyncio
async def test_owner_is_immutable_and_support_cannot_block(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'immutable-owner.db'}")
    await database.create_schema()
    owner, repository = await seed_users(database)
    support = AdminActor(
        telegram_user_id=303,
        role="support",
        permissions=ROLE_PERMISSIONS["support"],
    )

    with pytest.raises(ValueError, match="Власника"):
        await repository.block_user(owner, 101, "Неприпустима дія")
    with pytest.raises(PermissionError):
        await repository.block_user(support, 202, "Немає дозволу")
    await database.dispose()


@pytest.mark.asyncio
async def test_blocked_access_attempts_are_coalesced(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'blocked-events.db'}")
    await database.create_schema()
    _actor, repository = await seed_users(database)
    now = datetime(2026, 7, 24, 10, 3, tzinfo=UTC)

    await repository.record_blocked_access(202, "bot_group", now=now)
    await repository.record_blocked_access(202, "bot_group", now=now)

    async with database.session_factory() as session:
        event = (
            await session.scalars(
                select(BlockedAccessEvent).where(
                    BlockedAccessEvent.telegram_user_id == 202
                )
            )
        ).one()
    assert event.attempt_count == 2
    await database.dispose()


@pytest.mark.asyncio
async def test_notes_tags_and_xp_adjustments_preserve_invariants(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'admin-fields.db'}")
    await database.create_schema()
    actor, repository = await seed_users(database)

    note = await repository.set_note(actor, 202, "Важливий тестовий користувач")
    assert note["note"] == "Важливий тестовий користувач"
    await repository.add_tag(actor, 202, "  Тестер  ")
    adjustment = await repository.adjust_xp(actor, 202, 50, "Компенсація")
    assert adjustment["previous_total"] == 100
    assert adjustment["resulting_total"] == 150

    with pytest.raises(ValueError, match="від’ємним"):
        await repository.adjust_xp(actor, 202, -1000, "Надмірне списання")

    async with database.session_factory() as session:
        tag = await session.get(UserAdminTag, (202, "тестер"))
        user = await session.get(User, 202)
        adjustments = list(
            await session.scalars(
                select(UserXpAdjustment).where(UserXpAdjustment.telegram_user_id == 202)
            )
        )
    assert tag is not None
    assert user is not None and user.global_xp_total == 150
    assert len(adjustments) == 1
    await database.dispose()
