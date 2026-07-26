from __future__ import annotations

import hashlib
import hmac
import json
from datetime import UTC, datetime
from urllib.parse import urlencode


def signed_init_data(bot_token: str, telegram_user_id: int, *, now: datetime | None = None) -> str:
    current = now or datetime.now(UTC)
    values = {
        "auth_date": str(int(current.timestamp())),
        "query_id": f"load-{telegram_user_id}",
        "user": json.dumps(
            {"id": telegram_user_id, "first_name": "Load", "last_name": "Test"},
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(values)
