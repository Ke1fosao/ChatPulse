from collections.abc import Mapping, Sequence
from typing import Any

MEDALS = ("🥇", "🥈", "🥉")


def _message_word(count: int) -> str:
    if count % 10 == 1 and count % 100 != 11:
        return "повідомлення"
    if count % 10 in {2, 3, 4} and count % 100 not in {12, 13, 14}:
        return "повідомлення"
    return "повідомлень"


def format_group_stats(summary: Mapping[str, int]) -> str:
    if summary["messages_count"] == 0:
        return "📊 Поки що статистики немає. Напишіть перші повідомлення в групі."

    return (
        "📊 Статистика групи\n\n"
        f"💬 Повідомлень: {summary['messages_count']}\n"
        f"🖼 Медіа: {summary['media_count']}\n"
        f"↩️ Відповідей: {summary['replies_count']}\n"
        f"👥 Активних учасників: {summary['active_members']}"
    )


def format_top_members(members: Sequence[Mapping[str, Any]]) -> str:
    if not members:
        return "🏆 Рейтинг поки що порожній."

    lines = ["🏆 Топ учасників", ""]
    for index, member in enumerate(members, start=1):
        prefix = MEDALS[index - 1] if index <= len(MEDALS) else f"{index}."
        count = int(member["messages_count"])
        lines.append(f"{prefix} {member['display_name']} — {count} {_message_word(count)}")
    return "\n".join(lines)


def format_member_stats(member: Mapping[str, Any] | None) -> str:
    if member is None:
        return "👤 Для вас ще немає статистики в цій групі."

    return (
        f"👤 {member['display_name']}\n\n"
        f"💬 Повідомлень: {member['messages_count']}\n"
        f"🖼 Медіа: {member['media_count']}\n"
        f"↩️ Відповідей: {member['replies_count']}"
    )
