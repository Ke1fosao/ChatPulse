from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

from aiogram import Bot

from app.repositories.owner import OwnerRepository
from app.services.telegram_access_cache import TelegramAccessCache


@dataclass(frozen=True, slots=True)
class TelegramMemberSnapshot:
    status: str
    is_member: bool | None = None

    @property
    def has_membership(self) -> bool:
        if self.status in {"creator", "administrator", "member"}:
            return True
        if self.status == "restricted":
            return bool(self.is_member)
        return False

    @property
    def is_admin(self) -> bool:
        return self.status in {"creator", "administrator"}


class TelegramAccessService:
    MEMBER_POSITIVE_TTL = 60.0
    MEMBER_NEGATIVE_TTL = 15.0
    BOT_STATUS_TTL = 30.0
    STALE_GRACE = 300.0

    def __init__(
        self,
        bot: Bot | Any,
        *,
        owner_repository: OwnerRepository | None = None,
        cache: TelegramAccessCache[TelegramMemberSnapshot] | None = None,
        metrics: Any = None,
    ) -> None:
        self._bot = bot
        self._owner_repository = owner_repository
        self._bot_id: int | None = None
        self._metrics = metrics
        self._cache = cache or TelegramAccessCache(max_entries=10_000, metrics=metrics)

    def _record_call(self, operation: str, outcome: str, duration: float) -> None:
        if self._metrics is not None:
            self._metrics.telegram_calls.labels(operation=operation, outcome=outcome).inc()
            self._metrics.telegram_duration.labels(operation=operation).observe(duration)

    async def get_member_snapshot(
        self,
        chat_id: int,
        user_id: int,
    ) -> TelegramMemberSnapshot | None:
        cached = await self._cache.get_or_load(
            ("member", chat_id, user_id),
            lambda: self._load_member(chat_id, user_id),
            positive_ttl=self.MEMBER_POSITIVE_TTL,
            negative_ttl=self.MEMBER_NEGATIVE_TTL,
            stale_grace=self.STALE_GRACE,
            is_negative=lambda value: value is None or not value.has_membership,
        )
        return cached.value

    async def check_member(self, chat_id: int, user_id: int) -> bool:
        member = await self.get_member_snapshot(chat_id, user_id)
        return bool(member and member.has_membership)

    async def check_admin(self, chat_id: int, user_id: int) -> bool:
        if self._owner_repository is not None and await self._owner_repository.is_owner(user_id):
            return True
        member = await self.get_member_snapshot(chat_id, user_id)
        return bool(member and member.is_admin)

    async def get_bot_status(self, chat_id: int) -> str | None:
        bot_id = await self._resolve_bot_id()
        if bot_id is None:
            return None
        cached = await self._cache.get_or_load(
            ("bot", chat_id, bot_id),
            lambda: self._load_member(chat_id, bot_id),
            positive_ttl=self.BOT_STATUS_TTL,
            negative_ttl=self.MEMBER_NEGATIVE_TTL,
            stale_grace=self.STALE_GRACE,
            is_negative=lambda value: value is None,
        )
        return cached.value.status if cached.value is not None else None

    async def invalidate_user(self, chat_id: int, user_id: int) -> None:
        await self._cache.invalidate_user(chat_id, user_id)

    async def invalidate_group(self, chat_id: int) -> None:
        await self._cache.invalidate_group(chat_id)

    async def clear_cache(self) -> None:
        await self._cache.clear()

    async def _resolve_bot_id(self) -> int | None:
        if self._bot_id is not None:
            return self._bot_id
        started = time.perf_counter()
        try:
            bot_info = await self._bot.get_me()
        except Exception:
            self._record_call("get_me", "failed", time.perf_counter() - started)
            return None
        self._record_call("get_me", "success", time.perf_counter() - started)
        resolved = getattr(bot_info, "id", None)
        if resolved is None:
            return None
        self._bot_id = int(resolved)
        return self._bot_id

    async def _load_member(self, chat_id: int, user_id: int) -> TelegramMemberSnapshot:
        started = time.perf_counter()
        try:
            member = await self._bot.get_chat_member(chat_id, user_id)
        except Exception:
            self._record_call("get_chat_member", "failed", time.perf_counter() - started)
            raise
        self._record_call("get_chat_member", "success", time.perf_counter() - started)
        return TelegramMemberSnapshot(
            status=self._status_value(member),
            is_member=getattr(member, "is_member", None),
        )

    @staticmethod
    def _status_value(member: Any) -> str:
        status = getattr(member, "status", "")
        value = getattr(status, "value", status)
        return str(value).strip().lower()
