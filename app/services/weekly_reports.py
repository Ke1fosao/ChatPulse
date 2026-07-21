from datetime import datetime

from aiogram import Bot
from aiogram.types import BufferedInputFile, InlineKeyboardButton, InlineKeyboardMarkup

from app.repositories.activity import ActivityRepository
from app.repositories.gamification import GamificationRepository
from app.services.nominations import format_weekly_report
from app.services.report_cards import render_weekly_report_card
from app.services.weekly_payload import build_weekly_payload


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


async def _send_legacy_text_reports(
    bot: Bot,
    repository: ActivityRepository,
    *,
    now: datetime | None,
) -> int:
    sent = 0
    for group in await repository.list_due_weekly_reports(now=now):
        chat_id = int(group["telegram_chat_id"])
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
            continue
        await repository.mark_weekly_report_sent(chat_id, sent_at=now)
        sent += 1
    return sent


async def send_due_weekly_reports(
    bot: Bot,
    repository: ActivityRepository,
    *,
    now: datetime | None = None,
) -> int:
    if not hasattr(repository, "_session_factory"):
        return await _send_legacy_text_reports(bot, repository, now=now)

    sent = 0
    gamification_repository = GamificationRepository(repository._session_factory)
    for group in await repository.list_due_weekly_reports(now=now):
        chat_id = int(group["telegram_chat_id"])
        payload = await build_weekly_payload(
            repository,
            gamification_repository,
            chat_id,
            now=now,
        )
        reply_markup = _message_link_keyboard(payload)
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
        except Exception:
            try:
                await bot.send_message(
                    chat_id,
                    str(payload["text"]),
                    reply_markup=reply_markup,
                )
            except Exception:
                continue
        await repository.mark_weekly_report_sent(chat_id, sent_at=now)
        sent += 1
    return sent
