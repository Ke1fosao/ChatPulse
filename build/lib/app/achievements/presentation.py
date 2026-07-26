from __future__ import annotations

from typing import Any

from app.achievements.catalog import AchievementDefinition


def achievement_progress_payload(
    definition: AchievementDefinition,
    *,
    progress: int,
    earned: bool,
) -> dict[str, Any]:
    locked_secret = definition.hidden and not earned
    if locked_secret:
        return {
            "progress": 0,
            "threshold": 0,
            "comparator": definition.comparator,
        }

    safe_progress = max(progress, 0)
    public_progress = (
        safe_progress
        if definition.comparator == "lte"
        else min(safe_progress, definition.threshold)
    )
    return {
        "progress": public_progress,
        "threshold": definition.threshold,
        "comparator": definition.comparator,
    }
