from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any

from app.config import Settings
from app.observability.redaction import redact_value

_EXPECTED_EXCEPTION_NAMES = {
    "HTTPException",
    "RequestValidationError",
    "MiniAppAuthError",
}


def build_before_send(secrets: Sequence[str] = ()) -> Callable:
    safe_secrets = tuple(value for value in secrets if value)

    def scrub(event: dict[str, Any], hint: dict[str, Any] | None = None) -> dict[str, Any] | None:
        exception = (hint or {}).get("exc_info")
        if exception and exception[0].__name__ in _EXPECTED_EXCEPTION_NAMES:
            return None
        scrubbed = redact_value(event, secrets=safe_secrets)
        if isinstance(scrubbed, dict):
            request = scrubbed.get("request")
            if isinstance(request, dict):
                request.pop("data", None)
                request.pop("cookies", None)
                request.pop("query_string", None)
                request.pop("env", None)
                request.pop("headers", None)
            scrubbed.pop("user", None)
        return scrubbed

    return scrub


before_send = build_before_send()


def configure_sentry(settings: Settings) -> bool:
    if not settings.sentry_dsn:
        return False
    import sentry_sdk

    scrub = build_before_send(
        (
            settings.bot_token,
            settings.webhook_path_secret,
            settings.webhook_header_secret,
            settings.scheduler_secret or "",
            settings.internal_metrics_token or "",
            settings.redis_url or "",
            settings.database_url,
        )
    )
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment or settings.environment,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        send_default_pii=False,
        before_send=scrub,
    )
    return True
