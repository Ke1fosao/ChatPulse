from typing import Any

from app.services.gamification import level_tier, xp_threshold_for_level

MAX_LEVEL = 50

_TIER_REWARDS: dict[str, tuple[str, ...]] = {
    "Новачок": ("Базова аналітика", "Профіль ChatPulse"),
    "Бронза": ("Бронзовий бейдж", "Розширений прогрес"),
    "Срібло": ("Срібний бейдж", "Преміальна рамка картки"),
    "Золото": ("Золотий бейдж", "Покращена картка для поширення"),
    "Діамант": ("Діамантовий статус", "Максимальний престиж профілю"),
}


def build_level_catalog(*, current_level: int, xp_total: int) -> dict[str, Any]:
    safe_level = max(1, min(MAX_LEVEL, current_level))
    levels: list[dict[str, Any]] = []
    previous_tier = ""

    for level in range(1, MAX_LEVEL + 1):
        tier = level_tier(level)
        threshold = xp_threshold_for_level(level)
        next_threshold = (
            xp_threshold_for_level(level + 1) if level < MAX_LEVEL else None
        )
        tier_changed = tier != previous_tier
        rewards = list(_TIER_REWARDS[tier]) if tier_changed else []
        levels.append(
            {
                "level": level,
                "tier": tier,
                "xp_required": threshold,
                "xp_to_next": (
                    None if next_threshold is None else next_threshold - threshold
                ),
                "is_unlocked": level <= safe_level,
                "is_current": level == safe_level,
                "rewards": rewards,
            }
        )
        previous_tier = tier

    return {
        "current_level": safe_level,
        "xp_total": max(0, xp_total),
        "max_level": MAX_LEVEL,
        "levels": levels,
    }
