from __future__ import annotations

import json
import logging
from datetime import UTC, datetime
from typing import Any

from app.observability.redaction import redact_value
from app.observability.request_context import get_request_id

_STANDARD_RECORD_KEYS = set(logging.makeLogRecord({}).__dict__)


class JsonFormatter(logging.Formatter):
    def __init__(self, *, environment: str, version: str, revision: str | None = None) -> None:
        super().__init__()
        self.environment = environment
        self.version = version
        self.revision = revision

    def format(self, record: logging.LogRecord) -> str:
        fields: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname.lower(),
            "event": getattr(record, "event", record.getMessage()),
            "request_id": get_request_id(),
            "application_version": self.version,
            "environment": self.environment,
            "revision": self.revision,
        }
        for key, value in record.__dict__.items():
            if key not in _STANDARD_RECORD_KEYS and key not in {"event"}:
                fields[key] = value
        if record.exc_info:
            fields["exception_type"] = record.exc_info[0].__name__
        return json.dumps(redact_value(fields), ensure_ascii=False, default=str)


def configure_logging(*, production: bool, environment: str, version: str, revision: str | None) -> None:
    handler = logging.StreamHandler()
    if production:
        handler.setFormatter(JsonFormatter(environment=environment, version=version, revision=revision))
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)


def log_event(logger: logging.Logger, level: int, event: str, **fields: Any) -> None:
    logger.log(level, event, extra={"event": event, **redact_value(fields)})
