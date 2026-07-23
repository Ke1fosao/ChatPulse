import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from aiogram import Bot
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from app.repositories.activity import ActivityRepository
from app.repositories.gamification_v2 import AchievementGamificationRepository
from app.services.nominations import format_weekly_report
from app.services.report_cards import render_weekly_report_card
from app.services.retention_lifecycle import RetentionLifecycleService
from app.services.weekly_payload import build_weekly_payload

logger = logging.getLogger("chatpulse.weekly_reports")


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


async def _send_legacy_text_report(
    bot: Bot,
    repository: Any,
    chat_id: int,
    *,
    now: datetime | None,
    mark_sent: bool,
) -> bool:
    summary = await repository.get_group_summary(chat_id, "week", now=now)
    members = await repository.get_period_members(chat_id, "week", now=now)
    popular_reaction = await repository.get_popular_reaction(
        chat_id,
        "week",
        now=now,
    )
    try:
        await bot.send_message(
            chat_id,
            format_weekly_report(summary, members, popular_reaction),
        )
    except Exception:
        return False
    if mark_sent:
        await repository.mark_weekly_report_sent(chat_id, sent_at=now)
    return True


async def send_weekly_report(
    bot: Bot,
    repository: ActivityRepository,
    chat_id: int,
    *,
    now: datetime | None = None,
    retention_service: RetentionLifecycleService | None = None,
    mark_sent: bool = True,
) -> bool:
    if not hasattr(repository, "_session_factory"):
        return await _send_legacy_text_report(
            bot,
            repository,
            chat_id,
            now=now,
            mark_sent=mark_sent,
        )

    current = (now or datetime.now(UTC)).astimezone(UTC)
    report_start = current.date() - timedelta(days=current.weekday())
    gamification_repository = AchievementGamificationRepository(repository._session_factory)
    payload = await build_weekly_payload(
        repository,
        gamification_repository,
        chat_id,
        now=now,
    )
    reply_markup = _message_link_keyboard(payload)
    delivered = False
    try:
        image = render_weekly_report_card(payload, str(payload["theme"]))
        caption = str(payload["text"])
        if len(caption) > 1000:
            caption = caption[:997].rstrip() + "…"
        await bot.send_photo(
            chat_id,
            BufferedInputFile(image, filename="chatpulse-weekly.png"),
            caption=caption,
            reply_markup=reply_markup,
        )
        delivered = True
    except Exception:
        try:
            await bot.send_message(
                chat_id,
                str(payload["text"]),
                reply_markup=reply_markup,
            )
            delivered = True
        except Exception:
            return False

    if delivered and mark_sent:
        await repository.mark_weekly_report_sent(chat_id, sent_at=now)
    try:
        await gamification_repository.evaluate_weekly_achievements(
            chat_id,
            now=now,
        )
    except Exception:
        logger.exception("weekly_achievement_evaluation_failed chat_id=%s", chat_id)
    if retention_service is not None:
        try:
            await retention_service.notify_weekly_report(
                bot,
                chat_id=chat_id,
                group_title=str(payload["group_title"]),
                report_key=report_start.isoformat(),
                now=current,
            )
        except Exception:
            logger.exception("weekly_private_notification_failed chat_id=%s", chat_id)
    return delivered


async def _send_legacy_text_reports(
    bot: Bot,
    repository: ActivityRepository,
    *,
    now: datetime | None,
) -> int:
    sent = 0
    for group in await repository.list_due_weekly_reports(now=now):
        if await send_weekly_report(
            bot,
            repository,
            int(group["telegram_chat_id"]),
            now=now,
        ):
            sent += 1
    return sent


async def send_due_weekly_reports(
    bot: Bot,
    repository: ActivityRepository,
    *,
    now: datetime | None = None,
    retention_service: RetentionLifecycleService | None = None,
) -> int:
    if not hasattr(repository, "_session_factory"):
        return await _send_legacy_text_reports(bot, repository, now=now)

    sent = 0
    for group in await repository.list_due_weekly_reports(now=now):
        if await send_weekly_report(
            bot,
            repository,
            int(group["telegram_chat_id"]),
            now=now,
            retention_service=retention_service,
        ):
            sent += 1
    return sent
