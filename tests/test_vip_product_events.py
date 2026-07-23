from datetime import UTC, datetime

import pytest

from app.database import Database
from app.models import User
from app.repositories.vip_product_events import VipProductEventRepository


@pytest.fixture
async def vip_event_repository(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'vip-events.db'}")
    await database.create_schema()
    async with database.session_factory() as session, session.begin():
        session.add(User(telegram_id=7001, username="buyer", first_name="Buyer"))
    yield VipProductEventRepository(database.session_factory)
    await database.dispose()


@pytest.mark.asyncio
async def test_records_privacy_safe_vip_placement_event(vip_event_repository) -> None:
    event = await vip_event_repository.record(
        user_id=7001,
        event_type="vip_feature_previewed",
        source="group_analytics",
        feature_key="analytics.extended_history",
        metadata={"period": "year"},
        now=datetime(2026, 7, 23, 18, 0, tzinfo=UTC),
    )

    assert event["telegram_user_id"] == 7001
    assert event["event_type"] == "vip_feature_previewed"
    assert event["source"] == "group_analytics"
    assert event["feature_key"] == "analytics.extended_history"
    assert event["metadata"] == {"period": "year"}


@pytest.mark.asyncio
async def test_rejects_unknown_event_type_and_sensitive_metadata(vip_event_repository) -> None:
    with pytest.raises(ValueError, match="Unsupported VIP event"):
        await vip_event_repository.record(
            user_id=7001,
            event_type="message_text_captured",
            source="home",
            feature_key=None,
            metadata={},
        )

    with pytest.raises(ValueError, match="Sensitive metadata"):
        await vip_event_repository.record(
            user_id=7001,
            event_type="vip_viewed",
            source="profile",
            feature_key=None,
            metadata={"message_text": "secret"},
        )


@pytest.mark.asyncio
async def test_normalizes_source_and_limits_metadata(vip_event_repository) -> None:
    event = await vip_event_repository.record(
        user_id=7001,
        event_type="vip_viewed",
        source=" Profile VIP Card ",
        feature_key=None,
        metadata={"campaign": "trial"},
    )

    assert event["source"] == "profile_vip_card"
