from datetime import UTC, datetime, timedelta
from enum import StrEnum

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import ProcessedUpdate, utc_now

UPDATE_LEASE = timedelta(minutes=5)


class UpdateClaim(StrEnum):
    PROCESS = "process"
    COMPLETED_DUPLICATE = "completed_duplicate"
    IN_PROGRESS = "in_progress"


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class UpdateDeliveryRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def begin_update(
        self,
        update_id: int,
        update_type: str,
        *,
        now: datetime | None = None,
    ) -> UpdateClaim:
        current = _as_utc(now or utc_now())
        lease_expires_at = current + UPDATE_LEASE
        async with self._session_factory() as session:
            row = await session.get(ProcessedUpdate, update_id, with_for_update=True)
            if row is None:
                session.add(
                    ProcessedUpdate(
                        update_id=update_id,
                        update_type=update_type[:64] or "unknown",
                        status="processing",
                        attempts=1,
                        started_at=current,
                        lease_expires_at=lease_expires_at,
                        processed_at=current,
                    )
                )
                try:
                    await session.commit()
                except IntegrityError:
                    await session.rollback()
                    return await self.begin_update(update_id, update_type, now=current)
                return UpdateClaim.PROCESS

            if row.status == "completed":
                return UpdateClaim.COMPLETED_DUPLICATE

            existing_lease = _as_utc(row.lease_expires_at) if row.lease_expires_at else None
            if row.status == "processing" and existing_lease and existing_lease > current:
                return UpdateClaim.IN_PROGRESS

            row.update_type = update_type[:64] or "unknown"
            row.status = "processing"
            row.attempts = int(row.attempts or 0) + 1
            row.started_at = current
            row.lease_expires_at = lease_expires_at
            row.completed_at = None
            row.last_error = None
            row.processed_at = current
            await session.commit()
            return UpdateClaim.PROCESS

    async def complete_update(self, update_id: int, *, now: datetime | None = None) -> None:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            row = await session.get(ProcessedUpdate, update_id, with_for_update=True)
            if row is None:
                raise LookupError("Telegram update claim not found")
            row.status = "completed"
            row.completed_at = current
            row.lease_expires_at = None
            row.last_error = None
            row.processed_at = current

    async def fail_update(
        self,
        update_id: int,
        safe_error: str,
        *,
        now: datetime | None = None,
    ) -> None:
        current = _as_utc(now or utc_now())
        async with self._session_factory() as session, session.begin():
            row = await session.get(ProcessedUpdate, update_id, with_for_update=True)
            if row is None:
                raise LookupError("Telegram update claim not found")
            row.status = "failed"
            row.lease_expires_at = None
            row.last_error = (safe_error or "update_failed")[:128]
            row.processed_at = current
