from collections.abc import Mapping, Sequence
from typing import Any

METRICS = (
    ("messages_count", "🏆 Балакун тижня"),
    ("replies_count", "↩️ Майстер відповідей"),
    ("reactions_received", "❤️ Улюбленець групи"),
    ("photo_count", "📸 Фотограф групи"),
    ("voice_count", "🎤 Голос групи"),
    ("night_messages_count", "🌙 Нічний житель"),
    ("morning_messages_count", "🌅 Рання пташка"),
)


def build_nominations(members: Sequence[Mapping[str, Any]]) -> list[str]:
    lines: list[str] = []
    for metric, title in METRICS:
        candidates = [member for member in members if int(member.get(metric, 0)) > 0]
        if not candidates:
            continue
        winner = max(
            candidates,
            key=lambda item: (int(item[metric]), str(item["display_name"]).lower()),
        )
        lines.append(f"{title}: {winner['display_name']} — {int(winner[metric])}")
    return lines


def format_weekly_report(
    summary: Mapping[str, int],
    members: Sequence[Mapping[str, Any]],
    popular_reaction: tuple[str, int] | None,
) -> str:
    if summary["messages_count"] == 0 and summary["reactions_received"] == 0:
        return "📊 За останні 7 днів у групі ще не було активності."

    lines = [
        "📊 Підсумки тижня",
        "",
        f"💬 Повідомлень: {summary['messages_count']}",
        f"🖼 Медіа: {summary['media_count']}",
        f"↩️ Відповідей: {summary['replies_count']}",
        f"❤️ Реакцій: {summary['reactions_received']}",
        f"👥 Активних учасників: {summary['active_members']}",
    ]
    nominations = build_nominations(members)
    if nominations:
        lines.extend(["", "🎖 Номінації", *nominations])
    if popular_reaction is not None:
        emoji, count = popular_reaction
        lines.append(f"🔥 Найпопулярніша реакція: {emoji} — {count}")
    return "\n".join(lines)
