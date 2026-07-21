from collections.abc import Mapping, Sequence
from typing import Any

from app.domain import StatsPeriod

MEDALS = ("🥇", "🥈", "🥉")
PERIOD_LABELS: dict[StatsPeriod, str] = {
    "today": "сьогодні",
    "week": "за 7 днів",
    "month": "за місяць",
    "all": "за весь час",
}


def _message_word(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "повідомлення"
    return "повідомлень"


def format_group_stats(summary: Mapping[str, int], period: StatsPeriod = "all") -> str:
    if summary["messages_count"] == 0 and summary["reactions_received"] == 0:
        return f"📊 Статистики {PERIOD_LABELS[period]} поки немає."

    return (
        f"📊 Статистика {PERIOD_LABELS[period]}\n\n"
        f"💬 Повідомлень: {summary['messages_count']}\n"
        f"🖼 Медіа: {summary['media_count']}\n"
        f"↩️ Відповідей: {summary['replies_count']}\n"
        f"❤️ Отримано реакцій: {summary['reactions_received']}\n"
        f"👥 Активних учасників: {summary['active_members']}"
    )


def format_top_members(
    members: Sequence[Mapping[str, Any]],
    period: StatsPeriod = "all",
) -> str:
    if not members:
        return f"🏆 Рейтинг {PERIOD_LABELS[period]} поки порожній."

    lines = [f"🏆 Топ учасників {PERIOD_LABELS[period]}", ""]
    for index, member in enumerate(members, start=1):
        prefix = MEDALS[index - 1] if index <= len(MEDALS) else f"{index}."
        count = int(member["messages_count"])
        reactions = int(member["reactions_received"])
        lines.append(
            f"{prefix} {member['display_name']} — {count} {_message_word(count)}, "
            f"❤️ {reactions}"
        )
    return "\n".join(lines)


def format_member_stats(
    member: Mapping[str, Any] | None,
    period: StatsPeriod = "all",
) -> str:
    if member is None:
        return f"👤 Для вас ще немає статистики {PERIOD_LABELS[period]}."

    return (
        f"👤 {member['display_name']} — {PERIOD_LABELS[period]}\n\n"
        f"💬 Повідомлень: {member['messages_count']}\n"
        f"🖼 Медіа: {member['media_count']}\n"
        f"↩️ Відповідей: {member['replies_count']}\n"
        f"❤️ Отримано реакцій: {member['reactions_received']}"
    )
