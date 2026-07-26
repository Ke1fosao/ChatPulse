from __future__ import annotations

from typing import Any

from app.api.miniapp.responses.common import AccountAccessResponse, StrictResponse


class PremiumContextResponse(StrictResponse):
    account: AccountAccessResponse
    trial_available: bool
    active_subscription: dict[str, Any] | None = None


class YearSummaryResponse(StrictResponse):
    year: int
    messages_count: int
    xp_earned: int
    active_days: int
    groups_count: int
    best_streak: int
    top_month: int | None = None
    monthly_xp: list[dict[str, Any]]
    achievements_count: int


class PremiumAnalyticsResponse(StrictResponse):
    group: dict[str, Any]
    period: str
    days: int
    start: str
    end: str
    overview: dict[str, Any]
    activity_series: list[dict[str, Any]]
    comparison: dict[str, Any] | None = None
    trends: dict[str, float | int | None]


class RankingPlansResponse(StrictResponse):
    plans: dict[str, str]


class ReportThemeResponse(StrictResponse):
    report_card_theme: str


class PremiumEventResponse(StrictResponse):
    event: dict[str, Any]
