from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ReportTheme = Literal["dark_pulse", "telegram_wave", "clean_light"]
AdminRoleInput = Literal["admin", "moderator", "support"]
BulkAction = Literal[
    "grant_vip",
    "revoke_vip",
    "block",
    "unblock",
    "add_tag",
    "remove_tag",
    "message",
]


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


class UserBlockRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    confirmation: Literal["ЗАБЛОКУВАТИ"]


class UserUnblockRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    confirmation: Literal["РОЗБЛОКУВАТИ"]


class UserNoteRequest(BaseModel):
    note: str = Field(max_length=4000)
    confirmation: Literal["ЗБЕРЕГТИ НОТАТКУ"]


class UserTagRequest(BaseModel):
    tag: str = Field(min_length=1, max_length=32)
    confirmation: Literal["ДОДАТИ ТЕГ"]


class UserXpAdjustmentRequest(BaseModel):
    amount: int = Field(ge=-100_000, le=100_000)
    reason: str = Field(min_length=3, max_length=500)
    telegram_chat_id: int | None = None
    confirmation: Literal["ЗМІНИТИ XP"]

    @model_validator(mode="after")
    def require_nonzero_amount(self) -> "UserXpAdjustmentRequest":
        if self.amount == 0:
            raise ValueError("Зміна XP не може дорівнювати нулю.")
        return self


class UserRoleRequest(BaseModel):
    role: AdminRoleInput
    confirmation: Literal["ЗМІНИТИ РОЛЬ"]


class UserRoleRemoveRequest(BaseModel):
    reason: str = Field(min_length=3, max_length=500)
    confirmation: Literal["ЗНЯТИ РОЛЬ"]


class UserMessageRequest(BaseModel):
    message_text: str = Field(min_length=1, max_length=1000)
    confirmation: Literal["НАДІСЛАТИ"]


class UserBulkRequest(BaseModel):
    action: BulkAction
    user_ids: list[int] = Field(min_length=1, max_length=100)
    reason: str | None = Field(default=None, max_length=500)
    mode: Literal["permanent", "until"] | None = None
    expires_at: datetime | None = None
    tag: str | None = Field(default=None, max_length=32)
    message_text: str | None = Field(default=None, max_length=1000)
    confirmation: Literal["ВИКОНАТИ МАСОВУ ДІЮ"]

    @model_validator(mode="after")
    def validate_action_payload(self) -> "UserBulkRequest":
        self.user_ids = list(dict.fromkeys(self.user_ids))
        if self.action == "message" and len(self.user_ids) > 50:
            raise ValueError("Масове повідомлення можна надіслати максимум 50 користувачам.")
        if self.action in {"block", "unblock", "grant_vip", "revoke_vip"}:
            if not self.reason or len(self.reason.strip()) < 3:
                raise ValueError("Для цієї масової дії потрібна причина.")
        if self.action == "grant_vip":
            if self.mode is None:
                raise ValueError("Вибери режим VIP.")
            if self.mode == "until" and self.expires_at is None:
                raise ValueError("Для строкового VIP потрібна дата завершення.")
            if self.expires_at is not None and self.expires_at.tzinfo is None:
                self.expires_at = self.expires_at.replace(tzinfo=UTC)
        if self.action in {"add_tag", "remove_tag"} and not self.tag:
            raise ValueError("Для дії потрібен тег.")
        if self.action == "message" and not self.message_text:
            raise ValueError("Для дії потрібен текст повідомлення.")
        return self


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
