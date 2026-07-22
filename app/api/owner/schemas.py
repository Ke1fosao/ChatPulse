from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ReportTheme = Literal["dark_pulse", "telegram_wave", "clean_light"]


class VipGrantRequest(BaseModel):
    mode: Literal["permanent", "until"]
    expires_at: datetime | None = None
    reason: str = Field(min_length=3, max_length=300)
    confirmation: Literal["ВИДАТИ VIP"]

    @model_validator(mode="after")
    def validate_expiry(self) -> "VipGrantRequest":
        if self.mode == "until" and self.expires_at is None:
            raise ValueError("Для строкового VIP потрібна дата завершення.")
        if self.mode == "permanent" and self.expires_at is not None:
            raise ValueError("Безстроковий VIP не може мати дату завершення.")
        if self.expires_at is not None and self.expires_at.tzinfo is None:
            self.expires_at = self.expires_at.replace(tzinfo=UTC)
        return self


class VipRevokeRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=300)
    confirmation: Literal["ВІДКЛИКАТИ VIP"]


class OwnerGroupUpdate(BaseModel):
    is_active: bool | None = None
    is_paused: bool | None = None
    weekly_reports_enabled: bool | None = None
    report_card_theme: ReportTheme | None = None
    confirmation: Literal["ЗБЕРЕГТИ"]

    @model_validator(mode="after")
    def require_change(self) -> "OwnerGroupUpdate":
        if not self.model_dump(exclude={"confirmation"}, exclude_none=True):
            raise ValueError("Не вибрано жодної зміни.")
        return self
