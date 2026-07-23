from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock

import pytest

from app.database import Database
from app.models import User, VipGrant
from app.services.vip_lifecycle import VipLifecycleService


@pytest.mark.asyncio
async def test_sends_expiry_warning_once(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'vip-lifecycle.db'}")
    await database.create_schema()
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    async with database.session_factory() as session, session.begin():
        session.add(User(telegram_id=701, first_name="Warning"))
        session.add(
            VipGrant(
                telegram_user_id=701,
                is_active=True,
                starts_at=now - timedelta(days=5),
                expires_at=now + timedelta(days=2),
                granted_by_owner_id=1,
                grant_reason="paid VIP",
            )
        )

    bot = AsyncMock()
    service = VipLifecycleService(database.session_factory)
    first = await service.send_due(bot, now=now)
    second = await service.send_due(bot, now=now)

    assert first == {"warning_sent": 1, "expired_sent": 0}
    assert second == {"warning_sent": 0, "expired_sent": 0}
    bot.send_message.assert_awaited_once()
    await database.dispose()


@pytest.mark.asyncio
async def test_sends_expired_notification_once(tmp_path) -> None:
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'vip-expired.db'}")
    await database.create_schema()
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    async with database.session_factory() as session, session.begin():
        session.add(User(telegram_id=702, first_name="Expired"))
        session.add(
            VipGrant(
                telegram_user_id=702,
                is_active=True,
                starts_at=now - timedelta(days=10),
                expires_at=now - timedelta(hours=2),
                granted_by_owner_id=1,
                grant_reason="paid VIP",
            )
        )

    bot = AsyncMock()
    service = VipLifecycleService(database.session_factory)
    result = await service.send_due(bot, now=now)

    assert result == {"warning_sent": 0, "expired_sent": 1}
    bot.send_message.assert_awaited_once()
    await database.dispose()
