import hashlib
import hmac
import json
from datetime import UTC, datetime
from urllib.parse import parse_qsl

from pydantic import BaseModel, ConfigDict, Field


class MiniAppAuthError(ValueError):
    """Raised when Telegram Mini App init data cannot be trusted."""


class TelegramMiniAppUser(BaseModel):
    model_config = ConfigDict(frozen=True)

    telegram_id: int = Field(gt=0)
    first_name: str
    last_name: str | None = None
    username: str | None = None
    language_code: str | None = None
    photo_url: str | None = None
    auth_date: datetime
    query_id: str | None = None

    @property
    def display_name(self) -> str:
        parts = [self.first_name, self.last_name]
        return " ".join(part for part in parts if part).strip() or str(self.telegram_id)


def _utc_timestamp(value: datetime | None) -> int:
    current = value or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    return int(current.astimezone(UTC).timestamp())


def validate_init_data(
    init_data: str,
    bot_token: str,
    *,
    max_age_seconds: int = 900,
    now: datetime | None = None,
) -> TelegramMiniAppUser:
    if not init_data:
        raise MiniAppAuthError("Відсутні дані Telegram Mini App.")

    values = dict(parse_qsl(init_data, keep_blank_values=True, strict_parsing=False))
    received_hash = values.pop("hash", None)
    if not received_hash:
        raise MiniAppAuthError("У Telegram initData відсутній hash.")

    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    expected_hash = hmac.new(
        secret_key,
        data_check_string.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()
    if not hmac.compare_digest(received_hash, expected_hash):
        raise MiniAppAuthError("Невірний підпис Telegram Mini App.")

    try:
        auth_timestamp = int(values["auth_date"])
    except (KeyError, TypeError, ValueError) as error:
        raise MiniAppAuthError("Некоректна дата авторизації Telegram.") from error

    current_timestamp = _utc_timestamp(now)
    age = current_timestamp - auth_timestamp
    if age > max_age_seconds:
        raise MiniAppAuthError("Сесія Telegram Mini App прострочена.")
    if age < -30:
        raise MiniAppAuthError("Дата авторизації Telegram знаходиться у майбутньому.")

    try:
        raw_user = json.loads(values["user"])
        telegram_id = int(raw_user["id"])
        first_name = str(raw_user["first_name"])
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
        raise MiniAppAuthError("Не вдалося прочитати дані користувача Telegram.") from error

    return TelegramMiniAppUser(
        telegram_id=telegram_id,
        first_name=first_name,
        last_name=raw_user.get("last_name"),
        username=raw_user.get("username"),
        language_code=raw_user.get("language_code"),
        photo_url=raw_user.get("photo_url"),
        auth_date=datetime.fromtimestamp(auth_timestamp, tz=UTC),
        query_id=values.get("query_id"),
    )
