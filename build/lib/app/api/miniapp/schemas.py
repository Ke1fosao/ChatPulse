from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

MiniAppPeriod = Literal["week", "month", "all"]
RankingMetric = Literal["xp", "messages", "reactions", "replies", "streak"]
ReportTheme = Literal["dark_pulse", "telegram_wave", "clean_light"]


class GroupSettingsUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    is_paused: bool | None = None
    weekly_reports_enabled: bool | None = None
    timezone: Literal["Europe/Kyiv", "Europe/Warsaw", "Europe/Berlin"] | None = None
    report_weekday: int | None = Field(default=None, ge=0, le=6)
    report_time: str | None = None
    report_card_theme: ReportTheme | None = None
    track_messages: bool | None = None
    track_media: bool | None = None
    track_replies: bool | None = None
    track_reactions: bool | None = None

    @field_validator("report_time")
    @classmethod
    def validate_report_time(cls, value: str | None) -> str | None:
        if value is None:
            return None
        pieces = value.strip().split(":")
        if len(pieces) != 2 or not all(piece.isdigit() for piece in pieces):
            raise ValueError("Час має бути у форматі HH:MM.")
        hour, minute = (int(piece) for piece in pieces)
        if not 0 <= hour <= 23 or not 0 <= minute <= 59:
            raise ValueError("Година має бути 00–23, хвилини — 00–59.")
        return f"{hour:02d}:{minute:02d}"


class ResetGroupRequest(BaseModel):
    confirmation: str

    @field_validator("confirmation")
    @classmethod
    def validate_confirmation(cls, value: str) -> str:
        if value.strip().upper() != "СКИНУТИ":
            raise ValueError("Для підтвердження введіть СКИНУТИ.")
        return "СКИНУТИ"
