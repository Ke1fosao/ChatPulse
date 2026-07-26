from datetime import UTC, datetime

from app.api.miniapp.auth import validate_init_data
from load.identity import signed_init_data


def test_load_identity_has_valid_telegram_signature() -> None:
    now = datetime(2026, 7, 26, tzinfo=UTC)
    raw = signed_init_data("123456:test-token", 987654321, now=now)
    user = validate_init_data(raw, "123456:test-token", now=now)
    assert user.telegram_id == 987654321
    assert user.display_name == "Load Test"
