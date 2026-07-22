from datetime import datetime
from typing import Any

from app.repositories.activity import ActivityRepository
from app.repositories.gamification import GamificationRepository
from app.services.gamification import format_comparison
from app.services.nominations import build_nominations, format_weekly_report


async def build_weekly_payload(
    activity_repository: ActivityRepository,
    gamification_repository: GamificationRepository,
    chat_id: int,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    settings = await activity_repository.get_group_settings(chat_id)
    group_extras = await gamification_repository.get_group_extras(chat_id)
    summary = await activity_repository.get_group_summary(chat_id, "week", now=now)
    members = await activity_repository.get_period_members(chat_id, "week", now=now)
    popular_reaction = await activity_repository.get_popular_reaction(
        chat_id,
        "week",
        now=now,
    )
    current, previous = await gamification_repository.get_comparison(chat_id, now=now)
    top_message = await gamification_repository.get_top_message(chat_id, now=now)
    achievements = await gamification_repository.get_weekly_achievements(chat_id, now=now)
    nominations = build_nominations(members)

    text = format_weekly_report(summary, members, popular_reaction)
    extra_lines: list[str] = []
    comparison_text = format_comparison(current, previous)
    comparison_line = comparison_text.splitlines()[-1]
    extra_lines.extend(["", comparison_line])

    if top_message:
        extra_lines.extend(
            [
                "",
                f"🔥 Повідомлення тижня: {top_message['display_name']} — "
                f"{top_message['reactions_count']} реакцій",
            ]
        )
    if achievements:
        extra_lines.extend(["", "🏅 Нові досягнення"])
        extra_lines.extend(
            f"• {item['display_name']}: {item['title']}" for item in achievements[:6]
        )

    return {
        "group_title": (settings or {}).get("title", "ChatPulse"),
        "theme": group_extras.get("report_card_theme", "dark_pulse"),
        "summary": summary,
        "members": members,
        "popular_reaction": popular_reaction,
        "nominations": nominations,
        "comparison": {"current": current, "previous": previous},
        "comparison_line": comparison_line,
        "top_message": top_message,
        "achievements": achievements,
        "text": text + "\n".join(extra_lines),
    }
