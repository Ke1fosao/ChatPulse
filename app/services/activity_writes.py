from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.domain import GamificationUpdate, MessageActivity, UserData
from app.repositories.activity import ActivityRepository
from app.repositories.gamification import GamificationRepository

logger = logging.getLogger("chatpulse.transactions")


@dataclass(frozen=True, slots=True)
class ActivityWriteResult:
    tracked: bool
    gamification: GamificationUpdate = field(default_factory=GamificationUpdate)


@dataclass(frozen=True, slots=True)
class ReactionWriteResult:
    tracked: bool
    previous_total: int = 0
    current_total: int = 0
    gamification: GamificationUpdate = field(default_factory=GamificationUpdate)

    @property
    def positive_delta(self) -> int:
        return max(0, self.current_total - self.previous_total)


class ActivityWriteService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        activity_repository: ActivityRepository,
        gamification_repository: GamificationRepository,
    ) -> None:
        self._session_factory = session_factory
        self._activity = activity_repository
        self._gamification = gamification_repository

    async def record_message(
        self,
        *,
        chat_id: int,
        user: UserData,
        activity: MessageActivity,
        occurred_at: datetime,
        message_id: int,
    ) -> ActivityWriteResult:
        try:
            async with self._session_factory() as session, session.begin():
                tracked = await self._activity.record_message_in_session(
                    session,
                    chat_id=chat_id,
                    user=user,
                    activity=activity,
                    occurred_at=occurred_at,
                    message_id=message_id,
                )
                if not tracked:
                    return ActivityWriteResult(tracked=False)
                await session.flush()
                update = await self._gamification.award_message_xp_in_session(
                    session,
                    chat_id=chat_id,
                    user_id=user.telegram_id,
                    message_id=message_id,
                    activity=activity,
                    occurred_at=occurred_at,
                )
                return ActivityWriteResult(tracked=True, gamification=update)
        except Exception:
            logger.exception(
                "transaction_rolled_back operation=record_message chat_id=%s message_id=%s",
                chat_id,
                message_id,
            )
            raise

    async def record_reaction(
        self,
        *,
        chat_id: int,
        message_id: int,
        old_reactions: list[str],
        new_reactions: list[str],
        occurred_at: datetime,
    ) -> ReactionWriteResult:
        try:
            async with self._session_factory() as session, session.begin():
                tracked = await self._activity.record_reaction_in_session(
                    session,
                    chat_id=chat_id,
                    message_id=message_id,
                    old_reactions=old_reactions,
                    new_reactions=new_reactions,
                    occurred_at=occurred_at,
                )
                if not tracked:
                    return ReactionWriteResult(tracked=False)
                previous, current = await self._gamification.update_message_reaction_total_in_session(
                    session,
                    chat_id,
                    message_id,
                    delta=len(new_reactions) - len(old_reactions),
                )
                update = await self._gamification.award_reaction_xp_in_session(
                    session,
                    chat_id=chat_id,
                    message_id=message_id,
                    positive_delta=max(0, current - previous),
                    occurred_at=occurred_at,
                )
                return ReactionWriteResult(True, previous, current, update)
        except Exception:
            logger.exception(
                "transaction_rolled_back operation=record_reaction chat_id=%s message_id=%s",
                chat_id,
                message_id,
            )
            raise

    async def record_reaction_count(
        self,
        *,
        chat_id: int,
        message_id: int,
        reaction_counts: dict[str, int],
        occurred_at: datetime,
    ) -> ReactionWriteResult:
        try:
            async with self._session_factory() as session, session.begin():
                tracked = await self._activity.record_reaction_count_in_session(
                    session,
                    chat_id=chat_id,
                    message_id=message_id,
                    reaction_counts=reaction_counts,
                    occurred_at=occurred_at,
                )
                if not tracked:
                    return ReactionWriteResult(tracked=False)
                previous, current = await self._gamification.update_message_reaction_total_in_session(
                    session,
                    chat_id,
                    message_id,
                    total=sum(reaction_counts.values()),
                )
                update = await self._gamification.award_reaction_xp_in_session(
                    session,
                    chat_id=chat_id,
                    message_id=message_id,
                    positive_delta=max(0, current - previous),
                    occurred_at=occurred_at,
                )
                return ReactionWriteResult(True, previous, current, update)
        except Exception:
            logger.exception(
                "transaction_rolled_back operation=record_reaction_count chat_id=%s message_id=%s",
                chat_id,
                message_id,
            )
            raise
