from datetime import datetime

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.achievements.engine import AchievementEvent, AchievementSnapshot
from app.domain import AchievementEarned
from app.models import GroupMember, User
from app.repositories.achievements import AchievementRepository
from app.repositories.gamification import GamificationRepository


class AchievementGamificationRepository(GamificationRepository):
    """Adds Achievement System 2.0 without changing the stable XP pipeline."""

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__(session_factory)
        self._achievement_v2 = AchievementRepository(session_factory)

    async def _award_new_achievements(
        self,
        session: AsyncSession,
        member: GroupMember,
        timestamp: datetime,
    ) -> list[AchievementEarned]:
        user = await session.get(User, member.telegram_user_id)
        if user is None:
            return []

        snapshot = AchievementSnapshot(
            values={
                "messages_count": int(member.messages_count),
                "media_count": int(member.media_count),
                "replies_count": int(member.replies_count),
                "reactions_received": int(member.reactions_received),
                "photo_count": int(member.photo_count),
                "voice_count": int(member.voice_count),
                "night_messages_count": int(member.night_messages_count),
                "morning_messages_count": int(member.morning_messages_count),
                "xp_total": int(member.xp_total),
                "level": int(member.level),
                "current_streak": int(member.current_streak),
                "global_xp_total": int(user.global_xp_total),
                "global_level": int(user.global_level),
            }
        )
        events = tuple(
            AchievementEvent(
                trigger=trigger,
                telegram_user_id=member.telegram_user_id,
                telegram_chat_id=member.telegram_chat_id,
                occurred_at=timestamp,
            )
            for trigger in (
                "message_created",
                "reply_created",
                "media_created",
                "reaction_received",
                "streak_updated",
                "level_changed",
            )
        )
        return await self._achievement_v2.record_events(
            session,
            events=events,
            snapshot=snapshot,
        )
