from datetime import UTC

from aiogram import F, Router
from aiogram.enums import ChatType, ContentType
from aiogram.filters import Command
from aiogram.types import Message

from app.domain import GroupData, MessageActivity, UserData
from app.repositories.activity import ActivityRepository
from app.services.stats import format_group_stats, format_member_stats, format_top_members

router = Router(name="groups")
GROUP_TYPES = {ChatType.GROUP, ChatType.SUPERGROUP}
MEDIA_TYPES = {
    ContentType.PHOTO,
    ContentType.VIDEO,
    ContentType.AUDIO,
    ContentType.VOICE,
    ContentType.DOCUMENT,
    ContentType.ANIMATION,
    ContentType.VIDEO_NOTE,
    ContentType.STICKER,
}


def classify_message(message: Message) -> MessageActivity | None:
    sender = message.from_user
    if sender is None or sender.is_bot:
        return None

    command_source = message.text or message.caption or ""
    if command_source.lstrip().startswith("/"):
        return None

    return MessageActivity(
        is_media=message.content_type in MEDIA_TYPES,
        is_reply=message.reply_to_message is not None,
    )


def _user_data(message: Message) -> UserData | None:
    user = message.from_user
    if user is None:
        return None
    return UserData(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
        last_name=user.last_name,
        language_code=user.language_code,
    )


def _group_data(message: Message, timezone: str) -> GroupData:
    return GroupData(
        telegram_chat_id=message.chat.id,
        title=message.chat.title or "Telegram group",
        username=message.chat.username,
        timezone=timezone,
    )


@router.message(Command("stats"), F.chat.type.in_(GROUP_TYPES))
async def stats_command(message: Message, repository: ActivityRepository) -> None:
    summary = await repository.get_group_summary(message.chat.id)
    await message.answer(format_group_stats(summary))


@router.message(Command("top"), F.chat.type.in_(GROUP_TYPES))
async def top_command(message: Message, repository: ActivityRepository) -> None:
    members = await repository.get_top_members(message.chat.id, limit=10)
    await message.answer(format_top_members(members))


@router.message(Command("me"), F.chat.type.in_(GROUP_TYPES))
async def me_command(message: Message, repository: ActivityRepository) -> None:
    if message.from_user is None:
        return
    member = await repository.get_member_stats(message.chat.id, message.from_user.id)
    await message.answer(format_member_stats(member))


@router.message(Command("help"), F.chat.type.in_(GROUP_TYPES))
async def group_help_command(message: Message) -> None:
    await message.answer(
        "Команди ChatPulse:\n"
        "/stats — загальна статистика\n"
        "/top — рейтинг учасників\n"
        "/me — моя статистика\n\n"
        "Група активується автоматично після першого звичайного повідомлення."
    )


@router.message(F.chat.type.in_(GROUP_TYPES))
async def track_group_message(
    message: Message,
    repository: ActivityRepository,
    default_timezone: str,
) -> None:
    activity = classify_message(message)
    user = _user_data(message)
    if activity is None or user is None:
        return

    occurred_at = message.date
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)

    # Receiving an ordinary group message is sufficient proof that the bot is
    # present and can read the chat. Do not depend on a potentially missed
    # my_chat_member update to activate statistics.
    await repository.upsert_group(
        _group_data(message, default_timezone),
        bot_status="member",
        is_active=True,
    )
    await repository.record_message(
        chat_id=message.chat.id,
        user=user,
        activity=activity,
        occurred_at=occurred_at,
    )
