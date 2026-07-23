from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from math import ceil
from typing import Any

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import utc_now
from app.repositories.engagement import EngagementRepository
from app.repositories.miniapp_v2 import AchievementMiniAppRepository


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


class RetentionLifecycleService:
    def __init__(
        self,
        session_factory: async_sessionmaker[AsyncSession],
        *,
        miniapp_url: str | None = None,
    ) -> None:
        self._engagement = EngagementRepository(session_factory)
        self._achievements = AchievementMiniAppRepository(session_factory)
        self._miniapp_url = miniapp_url

    def _open_markup(self, label: str = "Відкрити ChatPulse") -> InlineKeyboardMarkup | None:
        if not self._miniapp_url:
            return None
        return InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text=label,
                        web_app=WebAppInfo(url=self._miniapp_url),
                    )
                ]
            ]
        )

    async def _deliver(
        self,
        bot: Bot,
        *,
        user_id: int,
        notification_type: str,
        notification_key: str,
        text: str,
        chat_id: int | None = None,
        now: datetime,
        button_label: str = "Відкрити ChatPulse",
    ) -> bool:
        notification_id = await self._engagement.claim_notification(
            user_id,
            notification_type=notification_type,
            notification_key=notification_key,
            chat_id=chat_id,
            now=now,
        )
        if notification_id is None:
            return False
        try:
            await bot.send_message(
                user_id,
                text,
                parse_mode="HTML",
                reply_markup=self._open_markup(button_label),
            )
        except Exception:
            await self._engagement.release_notification(notification_id)
            return False
        await self._engagement.mark_notification_sent(notification_id, now=now)
        return True

    async def send_due(self, bot: Bot, *, now: datetime | None = None) -> dict[str, int]:
        current = _as_utc(now or utc_now())
        streak_sent = 0
        achievement_sent = 0
        for user_id in await self._engagement.list_started_user_ids():
            streak = await self._engagement.get_streak_risk_candidate(user_id, now=current)
            if streak is not None:
                delivered = await self._deliver(
                    bot,
                    user_id=user_id,
                    notification_type="streak_risk",
                    notification_key=(
                        f"streak:{streak['telegram_chat_id']}:{streak['local_date']}"
                    ),
                    chat_id=int(streak["telegram_chat_id"]),
                    now=current,
                    text=(
                        "🔥 <b>Твоя серія сьогодні під загрозою</b>\n\n"
                        f"У групі <b>{streak['group_title']}</b> тримається серія "
                        f"<b>{streak['streak']} днів</b>. Напиши повідомлення до кінця дня, "
                        "щоб не втратити вогник."
                    ),
                    button_label="Перевірити серію",
                )
                if delivered:
                    streak_sent += 1
                continue

            achievement = await self._near_achievement(user_id)
            if achievement is None:
                continue
            remaining = int(achievement["threshold"]) - int(achievement["progress"])
            delivered = await self._deliver(
                bot,
                user_id=user_id,
                notification_type="achievement_near",
                notification_key=f"achievement:{achievement['code']}",
                now=current,
                text=(
                    "🏅 <b>Нове досягнення вже поруч</b>\n\n"
                    f"До «<b>{achievement['title']}</b>» залишилося лише "
                    f"<b>{remaining}</b>. Продовжуй активність — нагорода майже твоя."
                ),
                button_label="Відкрити досягнення",
            )
            if delivered:
                achievement_sent += 1

        return {
            "streak_sent": streak_sent,
            "achievement_sent": achievement_sent,
        }

    async def _near_achievement(self, user_id: int) -> dict[str, Any] | None:
        achievements = await self._achievements.get_achievements(user_id)
        if not achievements:
            return None
        candidates: list[dict[str, Any]] = []
        for item in achievements:
            if item.get("earned") or item.get("hidden"):
                continue
            threshold = int(item.get("threshold") or 0)
            progress = int(item.get("progress") or 0)
            if threshold <= 0 or progress <= 0 or progress >= threshold:
                continue
            remaining = threshold - progress
            near_limit = max(1, min(10, ceil(threshold * 0.1)))
            if remaining <= near_limit:
                candidates.append(item)
        if not candidates:
            return None
        return min(
            candidates,
            key=lambda item: (
                int(item["threshold"]) - int(item["progress"]),
                int(item["threshold"]),
            ),
        )

    async def notify_weekly_report(
        self,
        bot: Bot,
        *,
        chat_id: int,
        group_title: str,
        report_key: str,
        ranks: dict[int, int] | None = None,
        now: datetime | None = None,
    ) -> int:
        current = _as_utc(now or utc_now())
        try:
            period_start = date.fromisoformat(report_key)
        except ValueError:
            period_start = current.date() - timedelta(days=current.weekday())
        resolved_ranks = ranks or await self._engagement.get_group_xp_ranks(chat_id)
        user_ids = await self._engagement.list_weekly_user_ids(
            chat_id,
            since=current - timedelta(days=8),
        )
        sent = 0
        for user_id in user_ids:
            rank = resolved_ranks.get(user_id)
            rank_line = ""
            if rank is not None:
                change = await self._engagement.update_rank_snapshot(
                    user_id,
                    chat_id,
                    rank=rank,
                    period_start=period_start,
                    now=current,
                )
                improved_by = int(change["improved_by"] or 0)
                if improved_by > 0:
                    rank_line = (
                        f"\n🚀 Ти піднявся на <b>{improved_by} місця</b> "
                        f"і зараз займаєш <b>#{rank}</b>."
                    )
                else:
                    rank_line = f"\n📍 Твоє поточне місце: <b>#{rank}</b>."
            delivered = await self._deliver(
                bot,
                user_id=user_id,
                notification_type="weekly_report",
                notification_key=f"weekly:{chat_id}:{report_key}",
                chat_id=chat_id,
                now=current,
                text=(
                    "📊 <b>Звіт за тиждень готовий</b>\n\n"
                    f"У групі <b>{group_title}</b> вже можна переглянути нову статистику, "
                    f"рейтинг і досягнення.{rank_line}"
                ),
                button_label="Переглянути звіт",
            )
            if delivered:
                sent += 1
        return sent
