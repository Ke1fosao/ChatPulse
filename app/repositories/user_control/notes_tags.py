# ruff: noqa: F401, F403, F405, F821, I001
from .base import *  # noqa: F403
from .base import _as_utc, _display_name, _level_for_xp, _active_vip_clause


class UserNotesTagsMixin:
    async def set_note(self, actor: AdminActor, user_id: int, note: str) -> dict[str, Any]:
        actor.require("users.notes")
        normalized = note.strip()
        if len(normalized) > 4000:
            raise ValueError("Нотатка задовга.")
        current = _as_utc(utc_now())
        async with self._session_factory() as session, session.begin():
            await self._require_user(session, user_id)
            record = await session.get(UserAdminNote, user_id)
            if not normalized:
                if record is not None:
                    await session.delete(record)
            elif record is None:
                record = UserAdminNote(
                    telegram_user_id=user_id,
                    note=normalized,
                    updated_by_actor_id=actor.telegram_user_id,
                    updated_at=current,
                )
                session.add(record)
            else:
                record.note = normalized
                record.updated_by_actor_id = actor.telegram_user_id
                record.updated_at = current
            session.add(
                self._audit_entry(
                    actor,
                    action="user.note_updated",
                    target_id=user_id,
                    metadata={"has_note": bool(normalized), "length": len(normalized)},
                    created_at=current,
                )
            )
            return {
                "telegram_user_id": user_id,
                "note": normalized,
                "updated_at": current.isoformat(),
            }

    async def add_tag(self, actor: AdminActor, user_id: int, tag: str) -> dict[str, Any]:
        actor.require("users.notes")
        normalized = self._normalize_tag(tag)
        current = _as_utc(utc_now())
        async with self._session_factory() as session, session.begin():
            await self._require_user(session, user_id)
            count = int(
                await session.scalar(
                    select(func.count())
                    .select_from(UserAdminTag)
                    .where(UserAdminTag.telegram_user_id == user_id)
                )
                or 0
            )
            existing = await session.get(UserAdminTag, (user_id, normalized))
            if existing is None and count >= 10:
                raise ValueError("Для користувача вже встановлено максимум 10 тегів.")
            if existing is None:
                session.add(
                    UserAdminTag(
                        telegram_user_id=user_id,
                        tag=normalized,
                        created_by_actor_id=actor.telegram_user_id,
                        created_at=current,
                    )
                )
                session.add(
                    self._audit_entry(
                        actor,
                        action="user.tag_added",
                        target_id=user_id,
                        metadata={"tag": normalized},
                        created_at=current,
                    )
                )
            return {"telegram_user_id": user_id, "tag": normalized}

    async def remove_tag(self, actor: AdminActor, user_id: int, tag: str) -> dict[str, Any]:
        actor.require("users.notes")
        normalized = self._normalize_tag(tag)
        current = _as_utc(utc_now())
        async with self._session_factory() as session, session.begin():
            await self._require_user(session, user_id)
            result = await session.execute(
                delete(UserAdminTag).where(
                    UserAdminTag.telegram_user_id == user_id,
                    UserAdminTag.tag == normalized,
                )
            )
            if not result.rowcount:
                raise LookupError("Тег не знайдено.")
            session.add(
                self._audit_entry(
                    actor,
                    action="user.tag_removed",
                    target_id=user_id,
                    metadata={"tag": normalized},
                    created_at=current,
                )
            )
            return {"telegram_user_id": user_id, "tag": normalized, "removed": True}
