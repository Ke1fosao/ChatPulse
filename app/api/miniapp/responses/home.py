from __future__ import annotations

from typing import Any

from pydantic import Field

from app.api.miniapp.responses.common import AccountAccessResponse, StrictResponse


class HomeResponse(StrictResponse):
    user: dict[str, Any]
    account: AccountAccessResponse
    global_progress: dict[str, Any] = Field(default_factory=dict)
    quick_stats: dict[str, Any] = Field(default_factory=dict)
    activity_series: list[dict[str, Any]] = Field(default_factory=list)
    recent_achievements: list[dict[str, Any]] = Field(default_factory=list)
    groups: list[dict[str, Any]] = Field(default_factory=list)


class LevelsResponse(StrictResponse):
    current_level: int
    xp_total: int
    max_level: int
    levels: list[dict[str, Any]]
