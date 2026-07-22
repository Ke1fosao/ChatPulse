import hashlib
import hmac
import math
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import time
from typing import Any

from app.domain import AchievementEarned, GamificationUpdate, MessageActivity

GROUP_DAILY_XP_CAP = 200
GLOBAL_DAILY_XP_CAP = 400
STREAK_XP_THRESHOLD = 10
MONTHLY_PROTECTION_DAYS = 3
XP_COOLDOWN_SECONDS = 5
BURST_WINDOW_MINUTES = 10
MAX_LEVEL = 50
LEVEL_MILESTONES: dict[int, str] = {
    1: "Старт",
    5: "Бронза",
    10: "Срібло",
    20: "Золото",
    35: "Діамант",
    50: "Легенда",
}

_WORD_RE = re.compile(r"[\w']+", flags=re.UNICODE)
_SPACE_RE = re.compile(r"\s+")


@dataclass(frozen=True, slots=True)
class AchievementDefinition:
    code: str
    title: str
    description: str
    field: str
    threshold: int
    important: bool = False


ACHIEVEMENTS: tuple[AchievementDefinition, ...] = (
    AchievementDefinition("first_steps", "Перші кроки", "Набрано 10 XP у групі", "xp_total", 10),
    AchievementDefinition(
        "level_5", "Бронзовий старт", "Досягнуто 5 рівня у групі", "level", 5, True
    ),
    AchievementDefinition(
        "messages_100", "Перша сотня", "Надіслано 100 повідомлень", "messages_count", 100
    ),
    AchievementDefinition(
        "messages_1000",
        "Машина спілкування",
        "Надіслано 1 000 повідомлень",
        "messages_count",
        1000,
        True,
    ),
    AchievementDefinition(
        "reactions_100",
        "Улюбленець групи",
        "Отримано 100 реакцій",
        "reactions_received",
        100,
        True,
    ),
    AchievementDefinition(
        "replies_100", "Майстер діалогу", "Надіслано 100 відповідей", "replies_count", 100
    ),
    AchievementDefinition("photos_50", "Папараці", "Надіслано 50 фото", "photo_count", 50),
    AchievementDefinition("voices_25", "Голос чату", "Надіслано 25 голосових", "voice_count", 25),
    AchievementDefinition(
        "streak_7", "Тиждень у ритмі", "Серія активності 7 днів", "current_streak", 7, True
    ),
    AchievementDefinition(
        "streak_30", "Місяць без пауз", "Серія активності 30 днів", "current_streak", 30, True
    ),
)
ACHIEVEMENT_BY_CODE = {item.code: item for item in ACHIEVEMENTS}


def normalize_message_text(text: str | None) -> str:
    if not text:
        return ""
    return _SPACE_RE.sub(" ", text.casefold().strip())


def has_qualifying_text(text: str | None) -> bool:
    normalized = normalize_message_text(text)
    if len(normalized) < 3:
        return False
    return any(character.isalnum() for character in normalized)


def _secret_key(secret: str) -> bytes:
    return hashlib.sha256(secret.encode("utf-8")).digest()


def _keyed_digest(value: str, secret: str, *, size: int = 32) -> bytes:
    return hashlib.blake2b(
        value.encode("utf-8"), key=_secret_key(secret), digest_size=size
    ).digest()


def content_fingerprints(
    text: str | None,
    *,
    media_key: str | None,
    secret: str,
) -> tuple[str | None, int | None, int, bool]:
    normalized = normalize_message_text(text)
    qualifies = has_qualifying_text(normalized)
    source = normalized
    if media_key:
        media_digest = hmac.new(
            _secret_key(secret), media_key.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        source = f"{source}|media:{media_digest}" if source else f"media:{media_digest}"
    if not source:
        return None, None, len(normalized), qualifies

    exact = _keyed_digest(source, secret, size=32).hex()
    tokens = _WORD_RE.findall(normalized)
    if media_key:
        tokens.append(f"media:{media_key}")
    if not tokens:
        tokens = [source]

    weights = [0] * 64
    for token in tokens:
        token_hash = int.from_bytes(_keyed_digest(token, secret, size=8), "big")
        for bit in range(64):
            weights[bit] += 1 if token_hash & (1 << bit) else -1
    simhash = 0
    for bit, weight in enumerate(weights):
        if weight >= 0:
            simhash |= 1 << bit
    return exact, simhash, len(normalized), qualifies


def hamming_distance(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def is_near_duplicate(candidate: int | None, previous: Sequence[int | None]) -> bool:
    if candidate is None:
        return False
    return any(value is not None and hamming_distance(candidate, value) <= 3 for value in previous)


def message_base_xp(activity: MessageActivity) -> int:
    text_xp = 1 if activity.has_qualifying_text else 0
    media_xp = 2 if activity.is_photo or activity.is_voice else 0
    reply_xp = 2 if activity.is_reply and (activity.has_qualifying_text or media_xp > 0) else 0
    return text_xp + media_xp + reply_xp


def burst_multiplier(recent_messages: int) -> float:
    if recent_messages <= 20:
        return 1.0
    if recent_messages <= 30:
        return 0.5
    if recent_messages <= 40:
        return 0.25
    return 0.0


def adjusted_message_xp(base_xp: int, recent_messages: int) -> int:
    if base_xp <= 0:
        return 0
    multiplier = burst_multiplier(recent_messages)
    if multiplier <= 0:
        return 0
    return max(1, math.floor(base_xp * multiplier))


def xp_threshold_for_level(level: int) -> int:
    normalized = max(1, level)
    return 50 * (normalized - 1) * normalized


def level_for_xp(xp: int) -> int:
    safe_xp = max(0, xp)
    level = max(1, int((1 + math.sqrt(1 + 0.08 * safe_xp)) / 2))
    level = min(level, MAX_LEVEL)
    while level < MAX_LEVEL and xp_threshold_for_level(level + 1) <= safe_xp:
        level += 1
    while level > 1 and xp_threshold_for_level(level) > safe_xp:
        level -= 1
    return level


def level_tier(level: int) -> str:
    if level >= 50:
        return "Легенда"
    if level >= 35:
        return "Діамант"
    if level >= 20:
        return "Золото"
    if level >= 10:
        return "Срібло"
    if level >= 5:
        return "Бронза"
    return "Новачок"


def level_progress(xp: int) -> tuple[int, int, int]:
    level = level_for_xp(xp)
    if level >= MAX_LEVEL:
        return MAX_LEVEL, 0, 0
    current_floor = xp_threshold_for_level(level)
    next_floor = xp_threshold_for_level(level + 1)
    return level, max(0, xp - current_floor), next_floor - current_floor


def level_catalog(xp: int) -> dict[str, Any]:
    safe_xp = max(0, int(xp))
    current_level = level_for_xp(safe_xp)
    levels: list[dict[str, Any]] = []

    for level in range(1, MAX_LEVEL + 1):
        xp_required = xp_threshold_for_level(level)
        xp_to_next = (
            xp_threshold_for_level(level + 1) - xp_required if level < MAX_LEVEL else 0
        )
        milestone_label = LEVEL_MILESTONES.get(level)
        levels.append(
            {
                "level": level,
                "tier": level_tier(level),
                "xp_required": xp_required,
                "xp_to_next": xp_to_next,
                "unlocked": level <= current_level,
                "is_current": level == current_level,
                "is_milestone": milestone_label is not None,
                "milestone_label": milestone_label,
            }
        )

    next_tier = None
    for milestone_level, milestone_tier in LEVEL_MILESTONES.items():
        if milestone_level > current_level:
            next_tier = {
                "level": milestone_level,
                "tier": milestone_tier,
                "xp_required": xp_threshold_for_level(milestone_level),
            }
            break

    return {
        "max_level": MAX_LEVEL,
        "current_level": current_level,
        "next_tier": next_tier,
        "levels": levels,
    }


def parse_report_time(value: str) -> time:
    cleaned = value.strip()
    parts = cleaned.split(":")
    if len(parts) != 2 or not all(part.isdigit() for part in parts):
        raise ValueError("Вкажіть час у форматі HH:MM, наприклад 20:30.")
    hour, minute = (int(part) for part in parts)
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        raise ValueError("Година має бути 00–23, а хвилини 00–59.")
    return time(hour=hour, minute=minute)


def evaluate_achievements(
    stats: Mapping[str, Any], existing_codes: set[str]
) -> list[AchievementEarned]:
    earned: list[AchievementEarned] = []
    for definition in ACHIEVEMENTS:
        if definition.code in existing_codes:
            continue
        if int(stats.get(definition.field, 0)) < definition.threshold:
            continue
        earned.append(
            AchievementEarned(
                code=definition.code,
                title=definition.title,
                description=definition.description,
                important=definition.important,
            )
        )
    return earned


def format_gamification_announcement(display_name: str, update: GamificationUpdate) -> str | None:
    lines: list[str] = []
    if update.new_group_level > update.old_group_level:
        lines.append(
            f"⬆️ {display_name} отримує {update.new_group_level} рівень у цій групі "
            f"({level_tier(update.new_group_level)})!"
        )
    if update.new_global_level > update.old_global_level:
        lines.append(
            f"🌍 Загальний рівень ChatPulse: {update.new_global_level} "
            f"({level_tier(update.new_global_level)})"
        )
    important = [item for item in update.achievements if item.important]
    for item in important:
        lines.append(f"🏅 Досягнення «{item.title}» — {item.description}")
    return "\n".join(lines) if lines else None


def format_profile(profile: Mapping[str, Any]) -> str:
    group_xp = int(profile.get("group_xp_total", 0))
    global_xp = int(profile.get("global_xp_total", 0))
    group_level, group_progress, group_needed = level_progress(group_xp)
    global_level, global_progress, global_needed = level_progress(global_xp)
    achievements = profile.get("achievements", [])

    lines = [
        f"👤 {profile.get('display_name', 'Учасник')}",
        "",
        f"🏠 Група: рівень {group_level} · {level_tier(group_level)}",
        f"XP: {group_xp} · до наступного {group_progress}/{group_needed}",
        f"🌍 ChatPulse: рівень {global_level} · {level_tier(global_level)}",
        f"XP: {global_xp} · до наступного {global_progress}/{global_needed}",
        f"🔥 Серія: {int(profile.get('current_streak', 0))} дн.",
        f"🏆 Рекорд серії: {int(profile.get('longest_streak', 0))} дн.",
        f"🛡 Захисних днів цього місяця: {int(profile.get('protection_left', 3))}/3",
    ]
    if achievements:
        lines.extend(["", "🎖 Досягнення"])
        for item in achievements[-8:]:
            title = item.get("title", item.get("achievement_code", "Досягнення"))
            lines.append(f"• {title}")
    else:
        lines.extend(["", "🎖 Досягнень поки немає."])
    return "\n".join(lines)


def _percent_change(current: int, previous: int) -> str:
    if previous == 0:
        return "нове" if current > 0 else "0%"
    change = round((current - previous) / previous * 100)
    return f"{change:+d}%"


def format_comparison(current: Mapping[str, int], previous: Mapping[str, int]) -> str:
    metrics = (
        ("messages_count", "💬 Повідомлення"),
        ("reactions_received", "❤️ Реакції"),
        ("active_members", "👥 Активні учасники"),
        ("photo_count", "📸 Фото"),
        ("voice_count", "🎤 Голосові"),
    )
    lines = ["📈 Порівняння з попередніми 7 днями", ""]
    for key, label in metrics:
        old_value = int(previous.get(key, 0))
        new_value = int(current.get(key, 0))
        lines.append(
            f"{label}: {old_value} → {new_value} · {_percent_change(new_value, old_value)}"
        )

    old_activity = int(previous.get("messages_count", 0)) + int(
        previous.get("reactions_received", 0)
    )
    new_activity = int(current.get("messages_count", 0)) + int(current.get("reactions_received", 0))
    if new_activity > old_activity:
        conclusion = f"🔥 Група стала активнішою: {_percent_change(new_activity, old_activity)}"
    elif new_activity < old_activity:
        conclusion = f"🌙 Активність знизилася: {_percent_change(new_activity, old_activity)}"
    else:
        conclusion = "➖ Загальна активність не змінилася."
    lines.extend(["", conclusion])
    return "\n".join(lines)
