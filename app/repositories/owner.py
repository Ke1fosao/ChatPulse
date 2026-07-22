from datetime import datetime
from enum import StrEnum

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import BotOwner, utc_now

OWNER_KEY = "primary"
ALLOWED_OWNER_USERNAME = "veheblya"


class OwnerClaimResult(StrEnum):
    CLAIMED = "claimed"
    ALREADY_OWNER = "already_owner"
    USERNAME_MISMATCH = "username_mismatch"
    CLAIMED_BY_OTHER = "claimed_by_other"


def normalize_username(username: str | None) -> str:
    return (username or "").strip().removeprefix("@").casefold()


class OwnerRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

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

            normalized_username = normalize_username(username)
            if normalized_username != ALLOWED_OWNER_USERNAME:
                return OwnerClaimResult.USERNAME_MISMATCH

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
