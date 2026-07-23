from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from typing import Any, Mapping, TypedDict


class GroupStatusPayload(TypedDict):
    id: str
    label: str
    tone: str
    attention_reason: str | None


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _clamp(value: float, minimum: float = 0, maximum: float = 100) -> float:
    return max(minimum, min(maximum, value))


def derive_group_status(
    *,
    bot_operational: bool,
    is_paused: bool,
    last_activity_at: datetime | None,
    now: datetime | None = None,
) -> GroupStatusPayload:
    current = _as_utc(now or datetime.now(UTC))
    if not bot_operational:
        return {
            "id": "needs_setup",
            "label": "Потрібне налаштування",
            "tone": "warning",
            "attention_reason": "Надайте ChatPulse права адміністратора у групі.",
        }
    if is_paused:
        return {
            "id": "needs_setup",
            "label": "Аналітику призупинено",
            "tone": "warning",
            "attention_reason": "Відновіть збір статистики у налаштуваннях групи.",
        }
    if last_activity_at is None:
        return {
            "id": "inactive",
            "label": "Немає активності",
            "tone": "muted",
            "attention_reason": None,
        }

    age = current - _as_utc(last_activity_at)
    if age <= timedelta(hours=24):
        return {
            "id": "active",
            "label": "Активна",
            "tone": "success",
            "attention_reason": None,
        }
    if age <= timedelta(days=7):
        return {
            "id": "quiet",
            "label": "Тиха",
            "tone": "neutral",
            "attention_reason": None,
        }
    return {
        "id": "inactive",
        "label": "Неактивна",
        "tone": "muted",
        "attention_reason": None,
    }


def _message_component(current_messages: int, previous_messages: int) -> tuple[int, float]:
    if current_messages <= 0:
        return 0, -100.0 if previous_messages > 0 else 0.0
    if previous_messages <= 0:
        return 100, 100.0
    change = ((current_messages - previous_messages) / previous_messages) * 100
    return round(_clamp(50 + change / 2)), change


def _pulse_label(score: int) -> tuple[str, str]:
    if score <= 24:
        return "Майже тиша", "danger"
    if score <= 49:
        return "Тихо", "warning"
    if score <= 69:
        return "Стабільно", "neutral"
    if score <= 84:
        return "Активно", "success"
    return "Дуже активно", "excellent"


def calculate_group_pulse(
    current: Mapping[str, int],
    previous: Mapping[str, int],
    *,
    total_members: int,
    consecutive_active_days: int,
    period_days: int,
) -> dict[str, Any]:
    messages = max(0, int(current.get("messages_count", 0)))
    previous_messages = max(0, int(previous.get("messages_count", 0)))
    active_members = max(0, int(current.get("active_members", 0)))
    reactions = max(0, int(current.get("reactions_received", 0)))
    replies = max(0, int(current.get("replies_count", 0)))

    message_score, message_change = _message_component(messages, previous_messages)
    active_ratio = (active_members / max(total_members, 1)) * 100
    active_score = round(_clamp(active_ratio))
    engagement_ratio = ((reactions + replies) / max(messages, 1)) * 100
    engagement_score = round(_clamp(engagement_ratio))
    continuity_target = max(1, min(period_days, 7))
    continuity_score = round(
        _clamp((max(0, consecutive_active_days) / continuity_target) * 100)
    )

    score = round(
        message_score * 0.40
        + active_score * 0.25
        + engagement_score * 0.20
        + continuity_score * 0.15
    )
    label, tone = _pulse_label(score)

    positive_candidates: list[tuple[float, str]] = []
    negative_candidates: list[tuple[float, str]] = []
    if message_change > 0:
        positive_candidates.append(
            (abs(message_change), f"Повідомлень стало на {round(message_change)}% більше.")
        )
    elif message_change < 0:
        negative_candidates.append(
            (abs(message_change), f"Повідомлень стало на {round(abs(message_change))}% менше.")
        )
    if active_ratio >= 60:
        positive_candidates.append(
            (active_ratio, f"У розмові беруть участь {active_members} учасників.")
        )
    elif total_members > 0 and active_ratio < 25:
        negative_candidates.append(
            (25 - active_ratio, "До розмови долучається мало учасників.")
        )
    if engagement_ratio >= 40:
        positive_candidates.append(
            (engagement_ratio, "У групі багато відповідей і реакцій.")
        )
    elif messages > 0 and engagement_ratio < 10:
        negative_candidates.append((10 - engagement_ratio, "У повідомлень мало реакцій і відповідей."))
    if consecutive_active_days >= continuity_target:
        positive_candidates.append(
            (float(consecutive_active_days), f"Група активна {consecutive_active_days} днів поспіль.")
        )
    elif consecutive_active_days <= 1:
        negative_candidates.append((7.0, "Стабільна серія активності ще не сформувалася."))

    positive = max(positive_candidates, default=(0.0, None), key=lambda item: item[0])[1]
    negative = max(negative_candidates, default=(0.0, None), key=lambda item: item[0])[1]

    return {
        "score": score,
        "label": label,
        "tone": tone,
        "components": {
            "messages": message_score,
            "members": active_score,
            "engagement": engagement_score,
            "continuity": continuity_score,
        },
        "positive": positive,
        "negative": negative,
    }


def build_group_insights(
    *,
    rank_change: int | None = None,
    achievement_title: str | None = None,
    record_messages: int | None = None,
    record_date: date | None = None,
    consecutive_active_days: int = 0,
    leader_name: str | None = None,
    report_ready: bool = False,
) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    if rank_change and rank_change > 0:
        items.append(
            {
                "id": "rank_up",
                "kind": "ranking",
                "icon": "trending-up",
                "title": "Підйом у рейтингу",
                "description": f"Ви піднялися на {rank_change} місця.",
            }
        )
    if achievement_title:
        items.append(
            {
                "id": "achievement",
                "kind": "achievement",
                "icon": "award",
                "title": "Нове досягнення",
                "description": achievement_title,
            }
        )
    if record_messages and record_messages > 0:
        when = f" {record_date.strftime('%d.%m')}" if record_date else ""
        items.append(
            {
                "id": "record_day",
                "kind": "record",
                "icon": "bar-chart",
                "title": "Сильний день",
                "description": f"{record_messages} повідомлень{when} — найкращий результат періоду.",
            }
        )
    if consecutive_active_days >= 3:
        items.append(
            {
                "id": "continuity",
                "kind": "streak",
                "icon": "flame",
                "title": "Серія групи триває",
                "description": f"Група активна {consecutive_active_days} днів поспіль.",
            }
        )
    if leader_name:
        items.append(
            {
                "id": "leader",
                "kind": "leader",
                "icon": "crown",
                "title": "Лідер періоду",
                "description": leader_name,
            }
        )
    if report_ready:
        items.append(
            {
                "id": "report_ready",
                "kind": "report",
                "icon": "file-chart",
                "title": "Тижневий звіт готовий",
                "description": "Його можна відкрити або надіслати у групу.",
            }
        )
    if not items:
        items.append(
            {
                "id": "steady",
                "kind": "summary",
                "icon": "activity",
                "title": "Пульс формується",
                "description": "Продовжуйте спілкуватися — нові події з’являться тут.",
            }
        )
    return items[:5]
