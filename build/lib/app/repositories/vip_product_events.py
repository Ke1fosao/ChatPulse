import json
import re
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import utc_now
from app.vip_product_models import VipProductEvent

ALLOWED_EVENT_TYPES = {
    "vip_viewed",
    "vip_plan_selected",
    "vip_invoice_opened",
    "vip_payment_completed",
    "vip_payment_canceled",
    "vip_feature_previewed",
    "vip_feature_unlocked",
}
SENSITIVE_METADATA_KEYS = {
    "message",
    "message_text",
    "caption",
    "file",
    "file_id",
    "init_data",
    "token",
    "bot_token",
}
SOURCE_PATTERN = re.compile(r"[^a-z0-9]+")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _normalize_source(value: str) -> str:
    normalized = SOURCE_PATTERN.sub("_", value.strip().casefold()).strip("_")
    if not normalized:
        raise ValueError("VIP event source is required")
    return normalized[:64]


def _validate_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    if len(metadata) > 12:
        raise ValueError("VIP event metadata is too large")
    lowered = {str(key).casefold() for key in metadata}
    if lowered & SENSITIVE_METADATA_KEYS:
        raise ValueError("Sensitive metadata is not allowed")
    encoded = json.dumps(metadata, ensure_ascii=False, separators=(",", ":"))
    if len(encoded.encode("utf-8")) > 2048:
        raise ValueError("VIP event metadata is too large")
    return metadata


class VipProductEventRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record(
        self,
        *,
        user_id: int,
        event_type: str,
        source: str,
        feature_key: str | None,
        metadata: dict[str, Any] | None = None,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        if event_type not in ALLOWED_EVENT_TYPES:
            raise ValueError("Unsupported VIP event")
        normalized_source = _normalize_source(source)
        safe_metadata = _validate_metadata(metadata or {})
        created_at = _as_utc(now or utc_now())
        event = VipProductEvent(
            telegram_user_id=user_id,
            event_type=event_type,
            source=normalized_source,
            feature_key=feature_key[:96] if feature_key else None,
            metadata_json=json.dumps(safe_metadata, ensure_ascii=False, separators=(",", ":")),
            created_at=created_at,
        )
        async with self._session_factory() as session, session.begin():
            session.add(event)
            await session.flush()
        return {
            "id": int(event.id),
            "telegram_user_id": int(event.telegram_user_id),
            "event_type": event.event_type,
            "source": event.source,
            "feature_key": event.feature_key,
            "metadata": safe_metadata,
            "created_at": created_at.isoformat(),
        }
