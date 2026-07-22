import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from urllib.parse import urlencode

import pytest

from app.api.miniapp.auth import MiniAppAuthError, validate_init_data


def signed_init_data(*, bot_token: str, user: dict, auth_date: datetime) -> str:
    values = {
        "auth_date": str(int(auth_date.timestamp())),
        "query_id": "AAEAA-test-query",
        "user": json.dumps(user, ensure_ascii=False, separators=(",", ":")),
    }
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    values["hash"] = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()
    return urlencode(values)


def test_validate_init_data_accepts_valid_signed_user() -> None:
    now = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)
    init_data = signed_init_data(
        bot_token="123456:test-token",
        auth_date=now,
        user={
            "id": 9_223_372_036_854,
            "first_name": "Дмитро",
            "last_name": "Ковтунович",
            "username": "ke1fosao",
            "language_code": "uk",
            "photo_url": "https://example.test/avatar.jpg",
        },
    )

    result = validate_init_data(init_data, "123456:test-token", now=now)

    assert result.telegram_id == 9_223_372_036_854
    assert result.display_name == "Дмитро Ковтунович"
    assert result.username == "ke1fosao"
    assert result.photo_url == "https://example.test/avatar.jpg"


def test_validate_init_data_rejects_tampered_user() -> None:
    now = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)
    init_data = signed_init_data(
        bot_token="123456:test-token",
        auth_date=now,
        user={"id": 101, "first_name": "Dmytro"},
    ).replace("Dmytro", "Vika")

    with pytest.raises(MiniAppAuthError, match="підпис"):
        validate_init_data(init_data, "123456:test-token", now=now)


def test_validate_init_data_rejects_expired_auth_date() -> None:
    now = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)
    init_data = signed_init_data(
        bot_token="123456:test-token",
        auth_date=now - timedelta(minutes=16),
        user={"id": 101, "first_name": "Dmytro"},
    )

    with pytest.raises(MiniAppAuthError, match="простроч"):
        validate_init_data(init_data, "123456:test-token", now=now)


def test_validate_init_data_rejects_malformed_user_json() -> None:
    now = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)
    values = {
        "auth_date": str(int(now.timestamp())),
        "query_id": "AAEAA-test-query",
        "user": "not-json",
    }
    data_check_string = "\n".join(f"{key}={values[key]}" for key in sorted(values))
    secret_key = hmac.new(b"WebAppData", b"123456:test-token", hashlib.sha256).digest()
    values["hash"] = hmac.new(
        secret_key,
        data_check_string.encode(),
        hashlib.sha256,
    ).hexdigest()

    with pytest.raises(MiniAppAuthError, match="користувача"):
        validate_init_data(urlencode(values), "123456:test-token", now=now)


def test_validate_init_data_rejects_missing_hash() -> None:
    with pytest.raises(MiniAppAuthError, match="hash"):
        validate_init_data("auth_date=1&user=%7B%7D", "123456:test-token")
