from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

_REDACTED = "[REDACTED]"
_SENSITIVE_KEYS = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-telegram-init-data",
    "init_data",
    "initdata",
    "bot_token",
    "scheduler_secret",
    "webhook_header_secret",
    "webhook_path_secret",
    "payment_payload",
    "provider_payment_charge_id",
    "telegram_payment_charge_id",
    "private_note",
    "notes",
    "request_body",
    "body",
    "payload",
}


def _is_sensitive_key(key: str) -> bool:
    normalized = key.casefold().replace("-", "_")
    return normalized in {item.replace("-", "_") for item in _SENSITIVE_KEYS} or any(
        marker in normalized for marker in ("secret", "token", "password", "init_data")
    )


def redact_value(value: Any, *, secrets: Sequence[str] = ()) -> Any:
    secret_values = tuple(item for item in secrets if item)
    if isinstance(value, str):
        result = value
        for secret in secret_values:
            result = result.replace(secret, _REDACTED)
        return result
    if isinstance(value, Mapping):
        return {
            str(key): _REDACTED
            if _is_sensitive_key(str(key))
            else redact_value(item, secrets=secret_values)
            for key, item in value.items()
        }
    if isinstance(value, tuple):
        return tuple(redact_value(item, secrets=secret_values) for item in value)
    if isinstance(value, list):
        return [redact_value(item, secrets=secret_values) for item in value]
    if isinstance(value, set):
        return {redact_value(item, secrets=secret_values) for item in value}
    return value
