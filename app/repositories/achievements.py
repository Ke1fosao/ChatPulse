from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.achievement_models import AchievementEventRecord, AchievementUnlockRecord
from app.achievements.catalog import ACHIEVEMENT_BY_CODE
from app.achievements.engine import AchievementEvent, AchievementSnapshot, evaluate_event
from app.domain import AchievementEarned
from app.models import ChatGroup, MemberAchievement, utc_now


def achievement_scope_key(scope: str, chat_id: int | None) -> str:
    if scope == "global":
        return "global"
    if chat_id is None:
        raise ValueError("Group-scoped achievement requires chat_id")
    return f"group:{chat_id}"


class AchievementRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        self._session_factory = session_factory

    async def record_events(
        self,
        session: AsyncSession,
        *,
        events: Iterable[AchievementEvent],
        snapshot: AchievementSnapshot,
        create_events: bool = True,
    ) -> list[AchievementEarned]:
        event_list = list(events)
        if not event_list:
            return []

        user_id = event_list[0].telegram_user_id
        chat_id = event_list[0].telegram_chat_id
        scope_keys = {"global"}
        if chat_id is not None:
            scope_keys.add(achievement_scope_key("group", chat_id))

        existing_rows = await session.scalars(
            select(AchievementUnlockRecord.achievement_code).where(
                AchievementUnlockRecord.telegram_user_id == user_id,
                AchievementUnlockRecord.scope_key.in_(scope_keys),
            )
        )
        existing_codes = set(existing_rows.all())

        if chat_id is not None:
            legacy_rows = await session.scalars(
                select(MemberAchievement.achievement_code).where(
                    MemberAchievement.telegram_chat_id == chat_id,
                    MemberAchievement.telegram_user_id == user_id,
                )
            )
            existing_codes.update(legacy_rows.all())

        earned: list[AchievementEarned] = []
        for event in event_list:
            for unlock in evaluate_event(event, snapshot, existing_codes):
                definition = unlock.definition
                scope_key = achievement_scope_key(
                    definition.scope,
                    unlock.telegram_chat_id,
                )
                try:
                    async with session.begin_nested():
                        record = AchievementUnlockRecord(
                            telegram_user_id=unlock.telegram_user_id,
                            telegram_chat_id=unlock.telegram_chat_id,
                            scope=definition.scope,
                            scope_key=scope_key,
                            achievement_code=definition.code,
                            rarity=definition.rarity.value,
                            final_progress=unlock.progress,
                            definition_version=definition.version,
                            earned_at=unlock.occurred_at,
                        )
                        session.add(record)
                        await session.flush()
                        if create_events:
                            session.add(
                                AchievementEventRecord(
                                    telegram_user_id=unlock.telegram_user_id,
                                    achievement_unlock_id=record.id,
                                    event_type="unlock",
                                    payload_json="{}",
                                    created_at=unlock.occurred_at,
                                )
                            )
                        if unlock.telegram_chat_id is not None:
                            legacy = await session.get(
                                MemberAchievement,
                                (
                                    unlock.telegram_chat_id,
                                    unlock.telegram_user_id,
                                    definition.code,
                                ),
                            )
                            if legacy is None:
                                session.add(
                                    MemberAchievement(
                                        telegram_chat_id=unlock.telegram_chat_id,
                                        telegram_user_id=unlock.telegram_user_id,
                                        achievement_code=definition.code,
                                        earned_at=unlock.occurred_at,
                                    )
                                )
                        await session.flush()
                except IntegrityError:
                    continue

                existing_codes.add(definition.code)
                earned.append(
                    AchievementEarned(
                        code=definition.code,
                        title=definition.title,
                        description=definition.description,
                        important=definition.important,
                    )
                )
        return earned

    async def list_pending_events(
        self,
        user_id: int,
        *,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        safe_limit = min(max(limit, 1), 25)
        async with self._session_factory() as session, session.begin():
            rows = (
                await session.execute(
                    self._event_query()
                    .where(
                        AchievementEventRecord.telegram_user_id == user_id,
                        AchievementEventRecord.seen_at.is_(None),
                    )
                    .order_by(
                        AchievementEventRecord.created_at.asc(),
                        AchievementEventRecord.id.asc(),
                    )
                    .limit(safe_limit)
                )
            ).all()
            delivered_at = utc_now()
            result: list[dict[str, Any]] = []
            for event, unlock, group_title in rows:
                if event.delivered_at is None:
                    event.delivered_at = delivered_at
                payload = self._event_payload(event, unlock, group_title)
                if payload is not None:
                    result.append(payload)
            return result

    async def get_unlock_event(
        self,
        user_id: int,
        event_id: int,
    ) -> dict[str, Any] | None:
        async with self._session_factory() as session:
            row = (
                await session.execute(
                    self._event_query().where(
                        AchievementEventRecord.id == event_id,
                        AchievementEventRecord.telegram_user_id == user_id,
                        AchievementEventRecord.event_type == "unlock",
                    )
                )
            ).first()
            if row is None:
                return None
            event, unlock, group_title = row
            if unlock is None:
                return None
            return self._event_payload(event, unlock, group_title)

    async def mark_seen(self, user_id: int, event_id: int) -> bool:
        return await self._mark_event(user_id, event_id, field="seen_at")

    async def mark_shared(self, user_id: int, event_id: int) -> bool:
        return await self._mark_event(user_id, event_id, field="shared_at")

    async def _mark_event(self, user_id: int, event_id: int, *, field: str) -> bool:
        async with self._session_factory() as session, session.begin():
            event = await session.scalar(
                select(AchievementEventRecord).where(
                    AchievementEventRecord.id == event_id,
                    AchievementEventRecord.telegram_user_id == user_id,
                )
            )
            if event is None:
                return False
            if getattr(event, field) is None:
                setattr(event, field, utc_now())
            return True

    async def create_collection_update_event(
        self,
        user_id: int,
        *,
        count: int,
        rarest_codes: list[str],
        created_at: datetime | None = None,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            self.add_collection_update_event(
                session,
                user_id=user_id,
                count=count,
                rarest_codes=rarest_codes,
                created_at=created_at,
            )

    @staticmethod
    def add_collection_update_event(
        session: AsyncSession,
        *,
        user_id: int,
        count: int,
        rarest_codes: list[str],
        created_at: datetime | None = None,
    ) -> None:
        payload = json.dumps(
            {"count": max(count, 0), "rarest_codes": rarest_codes[:3]},
            ensure_ascii=False,
        )
        session.add(
            AchievementEventRecord(
                telegram_user_id=user_id,
                achievement_unlock_id=None,
                event_type="collection_update",
                payload_json=payload,
                created_at=created_at or utc_now(),
            )
        )

    @staticmethod
    def _event_query():
        return (
            select(
                AchievementEventRecord,
                AchievementUnlockRecord,
                ChatGroup.title,
            )
            .outerjoin(
                AchievementUnlockRecord,
                AchievementUnlockRecord.id == AchievementEventRecord.achievement_unlock_id,
            )
            .outerjoin(
                ChatGroup,
                ChatGroup.telegram_chat_id == AchievementUnlockRecord.telegram_chat_id,
            )
        )

    @classmethod
    def _event_payload(
        cls,
        event: AchievementEventRecord,
        unlock: AchievementUnlockRecord | None,
        group_title: str | None,
    ) -> dict[str, Any] | None:
        base = {
            "event_id": int(event.id),
            "event_type": event.event_type,
            "created_at": event.created_at.isoformat(),
        }
        if event.event_type == "collection_update":
            raw_payload = cls._safe_payload(event.payload_json)
            rarest_codes = [str(code) for code in raw_payload.get("rarest_codes", [])[:3]]
            achievements = []
            for code in rarest_codes:
                definition = ACHIEVEMENT_BY_CODE.get(code)
                if definition is None:
                    continue
                achievements.append(
                    definition.to_public_dict(
                        earned=True,
                        progress=definition.threshold,
                    )
                )
            return {
                **base,
                "summary": {
                    "count": max(int(raw_payload.get("count", 0)), 0),
                    "achievements": achievements,
                },
            }

        if unlock is None:
            return None
        definition = ACHIEVEMENT_BY_CODE.get(unlock.achievement_code)
        if definition is None:
            return None
        return {
            **base,
            "achievement": definition.to_public_dict(
                earned=True,
                progress=int(unlock.final_progress),
                earned_at=unlock.earned_at.isoformat(),
                group_title=str(group_title) if group_title is not None else None,
            ),
        }

    @staticmethod
    def _safe_payload(value: str) -> dict[str, Any]:
        try:
            payload = json.loads(value)
        except (TypeError, ValueError):
            return {}
        return payload if isinstance(payload, dict) else {}
