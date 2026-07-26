from __future__ import annotations

from typing import Any

from app.api.miniapp.responses.common import StrictResponse


class AchievementsResponse(StrictResponse):
    achievements: list[dict[str, Any]]


class AchievementEventsResponse(StrictResponse):
    events: list[dict[str, Any]]
