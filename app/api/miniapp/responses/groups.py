from __future__ import annotations

from typing import Any

from pydantic import Field

from app.api.miniapp.responses.common import CapabilitiesResponse, StrictResponse


class GroupsResponse(StrictResponse):
    groups: list[dict[str, Any]]


class FavoriteResponse(StrictResponse):
    telegram_chat_id: int
    is_favorite: bool


class GroupOverviewResponse(StrictResponse):
    group: dict[str, Any]
    period: str = "week"
    pulse: dict[str, Any] = Field(default_factory=dict)
    personal_progress: dict[str, Any] = Field(default_factory=dict)
    top_participants: list[dict[str, Any]] = Field(default_factory=list)
    insights: list[dict[str, Any]] = Field(default_factory=list)
    top_message: dict[str, Any] | None = None
    popular_reaction: dict[str, Any] | None = None
    settings: dict[str, Any] = Field(default_factory=dict)
    capabilities: CapabilitiesResponse | None = None


class GroupRankingResponse(StrictResponse):
    metric: str
    period: str
    rows: list[dict[str, Any]]
    current_user: dict[str, Any] | None = None


class GroupAnalyticsResponse(StrictResponse):
    group: dict[str, Any] = Field(default_factory=dict)
    period: str
    overview: dict[str, Any] = Field(default_factory=dict)
    activity_series: list[dict[str, Any]] = Field(default_factory=list)
    heatmap: list[dict[str, Any]] = Field(default_factory=list)
    popular_reaction: dict[str, Any] | None = None
    settings: dict[str, Any] = Field(default_factory=dict)


class GroupAwardsResponse(StrictResponse):
    group: dict[str, Any] = Field(default_factory=dict)
    period: str
    nominations: list[dict[str, Any]] = Field(default_factory=list)
    achievements: list[dict[str, Any]] = Field(default_factory=list)
    nearest: list[dict[str, Any]] = Field(default_factory=list)
    highlighted: dict[str, Any] | None = None


class PausedResponse(StrictResponse):
    telegram_chat_id: int
    is_paused: bool


class GroupSettingsResponse(StrictResponse):
    telegram_chat_id: int
    title: str
    username: str | None = None
    bot_status: str
    is_active: bool
    is_paused: bool
    weekly_reports_enabled: bool
    timezone: str
    report_weekday: int
    report_hour: int
    report_minute: int
    report_time: str
    report_card_theme: str
    track_messages: bool
    track_media: bool
    track_replies: bool
    track_reactions: bool
