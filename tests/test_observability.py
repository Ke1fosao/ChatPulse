from __future__ import annotations

import json
import logging

from app.observability.logging import JsonFormatter
from app.observability.redaction import redact_value
from app.observability.request_context import normalize_request_id, reset_request_id, set_request_id
from app.observability.sentry import build_before_send


def test_request_id_accepts_only_bounded_safe_values() -> None:
    assert normalize_request_id("request_1234") == "request_1234"
    generated = normalize_request_id("bad id")
    assert len(generated) == 32
    assert " " not in generated


def test_redaction_removes_nested_sensitive_values() -> None:
    result = redact_value(
        {
            "Authorization": "Bearer abc",
            "nested": {"init_data": "raw", "safe": "ok"},
            "message": "token=secret-value",
        },
        secrets=("secret-value",),
    )
    assert result["Authorization"] == "[REDACTED]"
    assert result["nested"]["init_data"] == "[REDACTED]"
    assert result["nested"]["safe"] == "ok"
    assert "secret-value" not in result["message"]


def test_json_formatter_has_stable_operational_fields_and_request_id() -> None:
    formatter = JsonFormatter(environment="test", version="0.15.0", revision="rev-1")
    token = set_request_id("request-1234")
    try:
        record = logging.LogRecord("test", logging.INFO, __file__, 1, "event", (), None)
        record.event = "unit_event"
        payload = json.loads(formatter.format(record))
    finally:
        reset_request_id(token)
    assert payload["event"] == "unit_event"
    assert payload["request_id"] == "request-1234"
    assert payload["environment"] == "test"
    assert payload["application_version"] == "0.15.0"
    assert payload["revision"] == "rev-1"


def test_sentry_scrubber_removes_request_data_user_and_configured_secrets() -> None:
    scrub = build_before_send(("database-password", "bot-secret"))
    event = {
        "request": {
            "headers": {"Authorization": "Bearer bot-secret"},
            "cookies": {"session": "secret"},
            "query_string": "tgWebAppData=raw",
            "data": {"message": "database-password"},
            "url": "https://example.test/safe",
        },
        "user": {"id": "123"},
        "extra": {"safe": "ok", "detail": "database-password"},
    }
    result = scrub(event, {})
    assert result is not None
    assert "user" not in result
    assert result["request"] == {"url": "https://example.test/safe"}
    assert result["extra"]["safe"] == "ok"
    assert "database-password" not in json.dumps(result)


def test_sentry_scrubber_suppresses_expected_http_errors() -> None:
    class HTTPException(Exception):
        pass

    scrub = build_before_send()
    assert scrub({}, {"exc_info": (HTTPException, HTTPException(), None)}) is None
