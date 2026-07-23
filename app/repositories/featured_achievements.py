from __future__ import annotations

from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.achievement_models import AchievementUnlockRecord, FeaturedAchievement
from app.achievements.catalog import ACHIEVEMENT_BY_CODE
from app.models import utc_now

MAX_FEATURED_ACHIEVEMENTS = 5


class FeaturedAchievementRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def list_featured(self, user_id: int) -> list[dict[str, Any]]:
        async with self._session_factory() as session:
            rows = list(
                (
                    await session.scalars(
                        select(FeaturedAchievement)
                        .where(FeaturedAchievement.telegram_user_id == user_id)
                        .order_by(FeaturedAchievement.slot.asc())
                    )
                ).all()
            )
            result: list[dict[str, Any]] = []
            for row in rows:
                definition = ACHIEVEMENT_BY_CODE.get(row.achievement_code)
                if definition is None:
                    continue
                payload = definition.to_public_dict(
                    earned=True,
                    progress=definition.threshold,
                )
                payload["slot"] = int(row.slot)
                payload["scope_key"] = row.scope_key
                result.append(payload)
            return result

    async def set_featured_codes(self, user_id: int, codes: list[str]) -> list[dict[str, Any]]:
        normalized = list(dict.fromkeys(code.strip() for code in codes if code.strip()))
        if len(normalized) > MAX_FEATURED_ACHIEVEMENTS:
            raise ValueError("Можна закріпити не більше пʼяти досягнень.")

        async with self._session_factory() as session, session.begin():
            selected: dict[str, AchievementUnlockRecord] = {}
            if normalized:
                rows = list(
                    (
                        await session.scalars(
                            select(AchievementUnlockRecord)
                            .where(
                                AchievementUnlockRecord.telegram_user_id == user_id,
                                AchievementUnlockRecord.achievement_code.in_(normalized),
                            )
                            .order_by(AchievementUnlockRecord.earned_at.desc())
                        )
                    ).all()
                )
                for row in rows:
                    selected.setdefault(row.achievement_code, row)
                missing = [code for code in normalized if code not in selected]
                if missing:
                    raise ValueError("Можна закріплювати лише отримані досягнення.")

            await session.execute(
                delete(FeaturedAchievement).where(FeaturedAchievement.telegram_user_id == user_id)
            )
            created_at = utc_now()
            for slot, code in enumerate(normalized, start=1):
                unlock = selected[code]
                session.add(
                    FeaturedAchievement(
                        telegram_user_id=user_id,
                        slot=slot,
                        scope_key=unlock.scope_key,
                        achievement_code=code,
                        created_at=created_at,
                    )
                )

        return await self.list_featured(user_id)
