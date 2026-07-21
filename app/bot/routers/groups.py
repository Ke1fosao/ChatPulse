from datetime import UTC

from aiogram import F, Router
from aiogram.enums import ChatType, ContentType
from aiogram.filters import Command
from aiogram.types import (
    BufferedInputFile,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

from app.bot.keyboards_stats import period_keyboard
from app.domain import GroupData, MessageActivity, StatsPeriod, UserData
from app.repositories.activity import ActivityRepository
from app.repositories.gamification import GamificationRepository
from app.services.gamification import (
    content_fingerprints,
    format_comparison,
    format_gamification_announcement,
    format_profile,
)
from app.services.report_cards import render_weekly_report_card
from app.services.stats import format_group_stats, format_member_stats, format_top_members
from app.services.weekly_payload import build_weekly_payload

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
PERIODS: set[str] = {"today", "week", "month", "all"}


def _media_unique_id(message: Message) -> str | None:
    if message.photo:
        return message.photo[-1].file_unique_id
    for attribute in (
        "voice",
        "video_note",
        "video",
        "audio",
        "document",
        "animation",
        "sticker",
    ):
        media = getattr(message, attribute, None)
        file_unique_id = getattr(media, "file_unique_id", None)
        if file_unique_id:
            return str(file_unique_id)
    return None


def classify_message(
    message: Message,
    fingerprint_secret: str | None = None,
) -> MessageActivity | None:
    sender = message.from_user
    if sender is None or sender.is_bot:
        return None
    command_source = message.text or message.caption or ""
    if command_source.lstrip().startswith("/"):
        return None
    if fingerprint_secret is None:
        fingerprint, simhash, length, qualifies = None, None, 0, False
    else:
        fingerprint, simhash, length, qualifies = content_fingerprints(
            command_source,
            media_key=_media_unique_id(message),
            secret=fingerprint_secret,
        )
    return MessageActivity(
        is_media=message.content_type in MEDIA_TYPES,
        is_reply=message.reply_to_message is not None,
        is_photo=message.content_type == ContentType.PHOTO,
        is_voice=message.content_type in {ContentType.VOICE, ContentType.VIDEO_NOTE},
        content_length=length,
        content_fingerprint=fingerprint,
        content_simhash=simhash,
        has_qualifying_text=qualifies,
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


def _period(value: str) -> StatsPeriod:
    return value if value in PERIODS else "week"  # type: ignore[return-value]


async def _send_stats(
    message: Message,
    repository: ActivityRepository,
    period: StatsPeriod,
    *,
    edit: bool = False,
) -> None:
    summary = await repository.get_group_summary(message.chat.id, period)
    method = message.edit_text if edit else message.answer
    await method(format_group_stats(summary, period), reply_markup=period_keyboard("stats"))


async def _send_top(
    message: Message,
    repository: ActivityRepository,
    period: StatsPeriod,
    *,
    edit: bool = False,
) -> None:
    members = await repository.get_top_members(message.chat.id, limit=10, period=period)
    method = message.edit_text if edit else message.answer
    await method(format_top_members(members, period), reply_markup=period_keyboard("top"))


async def _send_me(
    message: Message,
    repository: ActivityRepository,
    period: StatsPeriod,
    user_id: int,
    *,
    edit: bool = False,
) -> None:
    member = await repository.get_member_stats(message.chat.id, user_id, period)
    method = message.edit_text if edit else message.answer
    await method(format_member_stats(member, period), reply_markup=period_keyboard("me"))


def _message_link_keyboard(payload: dict) -> InlineKeyboardMarkup | None:
    top_message = payload.get("top_message")
    if not top_message or not top_message.get("url"):
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔥 Перейти до повідомлення тижня",
                    url=str(top_message["url"]),
                )
            ]
        ]
    )


async def _send_weekly_card(
    message: Message,
    repository: ActivityRepository,
    gamification_repository: GamificationRepository,
) -> None:
    payload = await build_weekly_payload(
        repository,
        gamification_repository,
        message.chat.id,
    )
    try:
        image = render_weekly_report_card(payload, str(payload["theme"]))
    except Exception:
        await message.answer(payload["text"], reply_markup=_message_link_keyboard(payload))
        return
    caption = str(payload["text"])
    if len(caption) > 1000:
        caption = caption[:997].rstrip() + "…"
    await message.answer_photo(
        BufferedInputFile(image, filename="chatpulse-weekly.png"),
        caption=caption,
        reply_markup=_message_link_keyboard(payload),
    )


@router.message(Command("stats"), F.chat.type.in_(GROUP_TYPES))
async def stats_command(message: Message, repository: ActivityRepository) -> None:
    await _send_stats(message, repository, "week")


@router.message(Command("today"), F.chat.type.in_(GROUP_TYPES))
async def today_command(message: Message, repository: ActivityRepository) -> None:
    await _send_stats(message, repository, "today")


@router.message(Command("week"), F.chat.type.in_(GROUP_TYPES))
async def week_command(message: Message, repository: ActivityRepository) -> None:
    await _send_stats(message, repository, "week")


@router.message(Command("month"), F.chat.type.in_(GROUP_TYPES))
async def month_command(message: Message, repository: ActivityRepository) -> None:
    await _send_stats(message, repository, "month")


@router.message(Command("all"), F.chat.type.in_(GROUP_TYPES))
async def all_command(message: Message, repository: ActivityRepository) -> None:
    await _send_stats(message, repository, "all")


@router.message(Command("top"), F.chat.type.in_(GROUP_TYPES))
async def top_command(message: Message, repository: ActivityRepository) -> None:
    await _send_top(message, repository, "week")


@router.message(Command("me"), F.chat.type.in_(GROUP_TYPES))
async def me_command(message: Message, repository: ActivityRepository) -> None:
    if message.from_user is not None:
        await _send_me(message, repository, "week", message.from_user.id)


@router.message(Command("profile"), F.chat.type.in_(GROUP_TYPES))
async def profile_command(
    message: Message,
    gamification_repository: GamificationRepository,
) -> None:
    target = message.from_user
    if message.reply_to_message and message.reply_to_message.from_user:
        target = message.reply_to_message.from_user
    if target is None:
        return
    profile = await gamification_repository.get_profile(message.chat.id, target.id)
    if profile is None:
        await message.answer("📊 Для цього учасника ще немає XP-профілю.")
        return
    await message.answer(format_profile(profile))


@router.message(Command("compare"), F.chat.type.in_(GROUP_TYPES))
async def compare_command(
    message: Message,
    gamification_repository: GamificationRepository,
) -> None:
    current, previous = await gamification_repository.get_comparison(message.chat.id)
    await message.answer(format_comparison(current, previous))


@router.message(Command("weekly"), F.chat.type.in_(GROUP_TYPES))
async def weekly_preview_command(
    message: Message,
    repository: ActivityRepository,
    gamification_repository: GamificationRepository,
) -> None:
    await _send_weekly_card(message, repository, gamification_repository)


@router.callback_query(F.data.startswith("stats:"))
async def stats_callback(callback: CallbackQuery, repository: ActivityRepository) -> None:
    if callback.message is None:
        return
    await _send_stats(
        callback.message,
        repository,
        _period(callback.data.split(":", 1)[1]),
        edit=True,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("top:"))
async def top_callback(callback: CallbackQuery, repository: ActivityRepository) -> None:
    if callback.message is None:
        return
    await _send_top(
        callback.message,
        repository,
        _period(callback.data.split(":", 1)[1]),
        edit=True,
    )
    await callback.answer()


@router.callback_query(F.data.startswith("me:"))
async def me_callback(callback: CallbackQuery, repository: ActivityRepository) -> None:
    if callback.message is None:
        return
    await _send_me(
        callback.message,
        repository,
        _period(callback.data.split(":", 1)[1]),
        callback.from_user.id,
        edit=True,
    )
    await callback.answer()


@router.message(Command("help"), F.chat.type.in_(GROUP_TYPES))
async def group_help_command(message: Message) -> None:
    await message.answer(
        "Команди ChatPulse:\n"
        "/stats — статистика з вибором періоду\n"
        "/today, /week, /month, /all — швидкі періоди\n"
        "/top — рейтинг учасників\n"
        "/me — моя базова статистика\n"
        "/profile — XP, рівні, серія та досягнення\n"
        "/compare — порівняння двох останніх 7-денних періодів\n"
        "/weekly — картка тижневого звіту\n"
        "/settings — налаштування для адміністратора\n"
        "/setreporttime 20:30 — точний час звіту"
    )


@router.message(F.chat.type.in_(GROUP_TYPES))
async def track_group_message(
    message: Message,
    repository: ActivityRepository,
    gamification_repository: GamificationRepository,
    default_timezone: str,
    fingerprint_secret: str,
) -> None:
    activity = classify_message(message, fingerprint_secret)
    user = _user_data(message)
    if activity is None or user is None:
        return

    occurred_at = message.date
    if occurred_at.tzinfo is None:
        occurred_at = occurred_at.replace(tzinfo=UTC)

    await repository.upsert_group(
        _group_data(message, default_timezone),
        bot_status="member",
        is_active=True,
    )
    tracked = await repository.record_message(
        chat_id=message.chat.id,
        user=user,
        activity=activity,
        occurred_at=occurred_at,
        message_id=message.message_id,
    )
    if not tracked:
        return
    update = await gamification_repository.award_message_xp(
        chat_id=message.chat.id,
        user_id=user.telegram_id,
        message_id=message.message_id,
        activity=activity,
        occurred_at=occurred_at,
    )
    announcement = format_gamification_announcement(user.display_name, update)
    if announcement:
        await message.answer(announcement)
