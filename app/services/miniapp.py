from datetime import date, datetime
from typing import Any


def percentage_change(current: int, previous: int) -> int | None:
    if previous == 0:
        return 100 if current > 0 else 0
    return round(((current - previous) / previous) * 100)


def message_link(chat_id: int, username: str | None, message_id: int) -> str | None:
    if username:
        return f"https://t.me/{username}/{message_id}"
    raw_chat_id = str(abs(chat_id))
    if raw_chat_id.startswith("100") and len(raw_chat_id) > 3:
        return f"https://t.me/c/{raw_chat_id[3:]}/{message_id}"
    return None


def json_value(value: Any) -> Any:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return value
