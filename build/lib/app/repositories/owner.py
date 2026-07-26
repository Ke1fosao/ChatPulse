from datetime import datetime
from enum import StrEnum

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import BotOwner, utc_now

OWNER_KEY = "primary"


class OwnerClaimResult(StrEnum):
    CLAIMED = "claimed"
    ALREADY_OWNER = "already_owner"
    ID_MISMATCH = "id_mismatch"
    USERNAME_MISMATCH = "id_mismatch"  # Backward-compatible alias for older callers/tests.
    CLAIMED_BY_OTHER = "claimed_by_other"


def normalize_username(username: str | None) -> str:
    return (username or "").strip().removeprefix("@").casefold()


class OwnerRepository:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        allowed_owner_id: int | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._allowed_owner_id = allowed_owner_id

    async def claim_owner(
        self,
        telegram_user_id: int,
        username: str | None,
        claimed_at: datetime | None = None,
    ) -> OwnerClaimResult:
        async with self._session_factory() as session:
            existing = await session.get(BotOwner, OWNER_KEY)
            if existing is not None:
                return self._existing_result(existing, telegram_user_id)

            if self._allowed_owner_id is None or telegram_user_id != self._allowed_owner_id:
                return OwnerClaimResult.ID_MISMATCH

            normalized_username = normalize_username(username) or f"id{telegram_user_id}"
            session.add(
                BotOwner(
                    owner_key=OWNER_KEY,
                    telegram_user_id=telegram_user_id,
                    claimed_username=normalized_username,
                    claimed_at=claimed_at or utc_now(),
                )
            )
            try:
                await session.commit()
            except IntegrityError:
                await session.rollback()
                existing = await session.get(BotOwner, OWNER_KEY)
                if existing is None:
                    raise
                return self._existing_result(existing, telegram_user_id)

        return OwnerClaimResult.CLAIMED

    async def is_owner(self, telegram_user_id: int) -> bool:
        async with self._session_factory() as session:
            owner = await session.get(BotOwner, OWNER_KEY)
            return owner is not None and int(owner.telegram_user_id) == telegram_user_id

    @staticmethod
    def _existing_result(owner: BotOwner, telegram_user_id: int) -> OwnerClaimResult:
        if int(owner.telegram_user_id) == telegram_user_id:
            return OwnerClaimResult.ALREADY_OWNER
        return OwnerClaimResult.CLAIMED_BY_OTHER
