from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain import GroupData
from app.models import ChatGroup, utc_now
from app.repositories.activity import ActivityRepository

PRIVILEGED_BOT_STATUSES = {"administrator", "creator"}
ACTIVE_BOT_STATUSES = {"member", "administrator", "creator", "restricted"}


def normalize_bot_status(status: str) -> str:
    return status.strip().lower()


async def upsert_group_from_message(
    repository: ActivityRepository,
    data: GroupData,
) -> None:
    """Refresh group metadata without downgrading known administrator privileges."""

    bot_status = "member"
    async with repository._session_factory() as session:
        group = await session.get(ChatGroup, data.telegram_chat_id)
        if (
            group is not None
            and normalize_bot_status(group.bot_status) in PRIVILEGED_BOT_STATUSES
        ):
            bot_status = normalize_bot_status(group.bot_status)

    await repository.upsert_group(
        data,
        bot_status=bot_status,
        is_active=True,
    )


async def reconcile_group_bot_status(
    session_factory: async_sessionmaker[AsyncSession],
    chat_id: int,
    status: str,
) -> bool:
    """Persist an authoritative Telegram membership status when it changed."""

    normalized = normalize_bot_status(status)
    if not normalized:
        return False

    async with session_factory() as session, session.begin():
        group = await session.get(ChatGroup, chat_id)
        if group is None:
            return False

        is_active = normalized in ACTIVE_BOT_STATUSES
        if (
            normalize_bot_status(group.bot_status) == normalized
            and group.is_active == is_active
        ):
            return False

        group.bot_status = normalized
        group.is_active = is_active
        group.updated_at = utc_now()
        await session.flush()
        return True
