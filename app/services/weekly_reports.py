from datetime import datetime

from aiogram import Bot

from app.repositories.activity import ActivityRepository
from app.services.nominations import format_weekly_report


async def send_due_weekly_reports(
    bot: Bot,
    repository: ActivityRepository,
    *,
    now: datetime | None = None,
) -> int:
    sent = 0
    for group in await repository.list_due_weekly_reports(now=now):
        chat_id = int(group["telegram_chat_id"])
        summary = await repository.get_group_summary(chat_id, "week", now=now)
        members = await repository.get_period_members(chat_id, "week", now=now)
        popular_reaction = await repository.get_popular_reaction(chat_id, "week", now=now)
        text = format_weekly_report(summary, members, popular_reaction)
        try:
            await bot.send_message(chat_id, text)
        except Exception:
            continue
        await repository.mark_weekly_report_sent(chat_id, sent_at=now)
        sent += 1
    return sent
