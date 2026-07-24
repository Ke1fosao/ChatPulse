from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.achievement_models import AchievementUnlockRecord, FeaturedAchievement
from app.achievements.catalog import ACHIEVEMENT_BY_CODE
from app.models import ChatGroup, MemberAchievement, utc_now

MAX_FEATURED_ACHIEVEMENTS = 5


@dataclass(frozen=True, slots=True)
class EarnedAchievementSource:
    achievement_code: str
    scope_key: str
    telegram_chat_id: int | None
    group_title: str | None
    earned_at: datetime
    progress: int


class FeaturedAchievementRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    @staticmethod
    def _chat_id_from_scope(scope_key: str) -> int | None:
        if scope_key == "global":
            return None
        prefix = "group:"
        if not scope_key.startswith(prefix):
            raise ValueError("Некоректне джерело досягнення.")
        try:
            return int(scope_key.removeprefix(prefix))
        except ValueError as error:
            raise ValueError("Некоректне джерело досягнення.") from error

    async def _source_for_identity(
        self,
        session: AsyncSession,
        *,
        user_id: int,
        code: str,
        scope_key: str,
    ) -> EarnedAchievementSource | None:
        definition = ACHIEVEMENT_BY_CODE.get(code)
        if definition is None:
            return None

        canonical = await session.scalar(
            select(AchievementUnlockRecord).where(
                AchievementUnlockRecord.telegram_user_id == user_id,
                AchievementUnlockRecord.achievement_code == code,
                AchievementUnlockRecord.scope_key == scope_key,
            )
        )
        if canonical is not None:
            group_title = None
            if canonical.telegram_chat_id is not None:
                group = await session.get(ChatGroup, int(canonical.telegram_chat_id))
                group_title = group.title if group is not None else None
            return EarnedAchievementSource(
                achievement_code=code,
                scope_key=scope_key,
                telegram_chat_id=(
                    int(canonical.telegram_chat_id)
                    if canonical.telegram_chat_id is not None
                    else None
                ),
                group_title=group_title,
                earned_at=canonical.earned_at,
                progress=max(int(canonical.final_progress), int(definition.threshold)),
            )

        chat_id = self._chat_id_from_scope(scope_key)
        if chat_id is None:
            return None
        legacy = await session.get(MemberAchievement, (chat_id, user_id, code))
        if legacy is None:
            return None
        group = await session.get(ChatGroup, chat_id)
        return EarnedAchievementSource(
            achievement_code=code,
            scope_key=scope_key,
            telegram_chat_id=chat_id,
            group_title=group.title if group is not None else None,
            earned_at=legacy.earned_at,
            progress=int(definition.threshold),
        )

    @staticmethod
    def _serialize_source(
        source: EarnedAchievementSource,
        *,
        slot: int,
    ) -> dict[str, Any]:
        definition = ACHIEVEMENT_BY_CODE[source.achievement_code]
        earned_at = source.earned_at.isoformat()
        payload = definition.to_public_dict(
            earned=True,
            progress=source.progress,
            earned_at=earned_at,
            group_title=source.group_title,
        )
        payload.update(
            {
                "slot": slot,
                "scope_key": source.scope_key,
                "primary_scope_key": source.scope_key,
                "earned_instances": [
                    {
                        "scope_key": source.scope_key,
                        "telegram_chat_id": source.telegram_chat_id,
                        "group_title": source.group_title,
                        "earned_at": earned_at,
                        "progress": source.progress,
                    }
                ],
            }
        )
        return payload

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
                source = await self._source_for_identity(
                    session,
                    user_id=user_id,
                    code=row.achievement_code,
                    scope_key=row.scope_key,
                )
                if source is None:
                    continue
                result.append(self._serialize_source(source, slot=int(row.slot)))
            return result

    async def set_featured_items(
        self,
        user_id: int,
        items: list[dict[str, str]],
    ) -> list[dict[str, Any]]:
        normalized: list[tuple[str, str]] = []
        seen: set[tuple[str, str]] = set()
        for item in items:
            code = str(item.get("code", "")).strip()
            scope_key = str(item.get("scope_key", "")).strip()
            identity = (code, scope_key)
            if not code or not scope_key or identity in seen:
                continue
            seen.add(identity)
            normalized.append(identity)

        if len(normalized) > MAX_FEATURED_ACHIEVEMENTS:
            raise ValueError("Можна закріпити не більше пʼяти досягнень.")

        async with self._session_factory() as session, session.begin():
            selected: list[EarnedAchievementSource] = []
            for code, scope_key in normalized:
                source = await self._source_for_identity(
                    session,
                    user_id=user_id,
                    code=code,
                    scope_key=scope_key,
                )
                if source is None:
                    raise ValueError("Можна закріплювати лише отримані досягнення.")
                selected.append(source)

            await session.execute(
                delete(FeaturedAchievement).where(FeaturedAchievement.telegram_user_id == user_id)
            )
            created_at = utc_now()
            for slot, source in enumerate(selected, start=1):
                session.add(
                    FeaturedAchievement(
                        telegram_user_id=user_id,
                        slot=slot,
                        scope_key=source.scope_key,
                        achievement_code=source.achievement_code,
                        created_at=created_at,
                    )
                )

        return await self.list_featured(user_id)

    async def set_featured_codes(self, user_id: int, codes: list[str]) -> list[dict[str, Any]]:
        normalized_codes = list(dict.fromkeys(code.strip() for code in codes if code.strip()))
        if len(normalized_codes) > MAX_FEATURED_ACHIEVEMENTS:
            raise ValueError("Можна закріпити не більше пʼяти досягнень.")

        resolved: list[dict[str, str]] = []
        async with self._session_factory() as session:
            for code in normalized_codes:
                canonical = await session.scalar(
                    select(AchievementUnlockRecord)
                    .where(
                        AchievementUnlockRecord.telegram_user_id == user_id,
                        AchievementUnlockRecord.achievement_code == code,
                    )
                    .order_by(AchievementUnlockRecord.earned_at.desc())
                    .limit(1)
                )
                if canonical is not None:
                    resolved.append({"code": code, "scope_key": canonical.scope_key})
                    continue

                legacy = await session.scalar(
                    select(MemberAchievement)
                    .where(
                        MemberAchievement.telegram_user_id == user_id,
                        MemberAchievement.achievement_code == code,
                    )
                    .order_by(MemberAchievement.earned_at.desc())
                    .limit(1)
                )
                if legacy is None:
                    raise ValueError("Можна закріплювати лише отримані досягнення.")
                resolved.append(
                    {
                        "code": code,
                        "scope_key": f"group:{int(legacy.telegram_chat_id)}",
                    }
                )

        return await self.set_featured_items(user_id, resolved)
