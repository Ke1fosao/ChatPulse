from __future__ import annotations

from aiogram import Bot, Router
from aiogram.enums import ChatMemberStatus, ChatType
from aiogram.types import ChatMemberUpdated

from app.domain import GroupData, UserData
from app.repositories.activity import ActivityRepository
from app.repositories.engagement import EngagementRepository

router = Router(name="onboarding")
GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}
ACTIVE_STATUSES = {
    ChatMemberStatus.MEMBER,
    ChatMemberStatus.ADMINISTRATOR,
    ChatMemberStatus.CREATOR,
    ChatMemberStatus.RESTRICTED,
}
ADMIN_STATUSES = {ChatMemberStatus.ADMINISTRATOR, ChatMemberStatus.CREATOR}


def _user_data(event: ChatMemberUpdated) -> UserData:
    user = event.from_user
    return UserData(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
    )


@router.my_chat_member()
async def bot_membership_changed(
    event: ChatMemberUpdated,
    bot: Bot,
    repository: ActivityRepository,
    engagement_repository: EngagementRepository,
    default_timezone: str,
) -> None:
    if event.chat.type not in GROUP_TYPES:
        return

    new_status = event.new_chat_member.status
    old_status = event.old_chat_member.status
    is_active = new_status in ACTIVE_STATUSES
    status_value = new_status.value if hasattr(new_status, "value") else str(new_status)

    user = _user_data(event)
    await repository.upsert_user(user)
    await repository.upsert_group(
        GroupData(
            telegram_chat_id=event.chat.id,
            title=event.chat.title or "Telegram group",
            username=event.chat.username,
            timezone=default_timezone,
        ),
        bot_status=status_value,
        is_active=is_active,
    )
    await engagement_repository.link_group(
        user.telegram_id,
        event.chat.id,
        bot_status=status_value,
        now=event.date,
    )

    if new_status == old_status or not is_active:
        return
    if new_status in ADMIN_STATUSES and old_status not in ADMIN_STATUSES:
        await bot.send_message(
            event.chat.id,
            "⚡ <b>2/3 — права готові</b>\n\n"
            "ChatPulse уже може збирати дозволену статистику. Напиши перше звичайне "
            "повідомлення в групі — і з’являться XP, серія та аналітика.\n\n"
            "Тексти повідомлень і файли не зберігаються.",
            parse_mode="HTML",
        )
        return
    if old_status not in ACTIVE_STATUSES:
        await bot.send_message(
            event.chat.id,
            "✅ <b>1/3 — ChatPulse додано</b>\n\n"
            "Щоб аналітика працювала стабільно, признач бота адміністратором. "
            "Після цього достатньо одного звичайного повідомлення для першого пульсу.",
            parse_mode="HTML",
        )
