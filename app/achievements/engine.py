from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Mapping

from app.achievements.catalog import (
    AchievementDefinition,
    AchievementScope,
    AchievementTrigger,
    definitions_for_trigger,
)


@dataclass(frozen=True, slots=True)
class AchievementEvent:
    trigger: AchievementTrigger
    telegram_user_id: int
    telegram_chat_id: int | None
    occurred_at: datetime


@dataclass(frozen=True, slots=True)
class AchievementSnapshot:
    values: Mapping[str, int]

    def value(self, metric: str) -> int:
        return int(self.values.get(metric, 0))


@dataclass(frozen=True, slots=True)
class AchievementUnlock:
    definition: AchievementDefinition
    progress: int
    telegram_user_id: int
    telegram_chat_id: int | None
    occurred_at: datetime

    @property
    def code(self) -> str:
        return self.definition.code

    @property
    def scope(self) -> AchievementScope:
        return self.definition.scope


def _matches(definition: AchievementDefinition, value: int) -> bool:
    if definition.comparator == "lte":
        return value > 0 and value <= definition.threshold
    return value >= definition.threshold


def evaluate_event(
    event: AchievementEvent,
    snapshot: AchievementSnapshot,
    existing_codes: set[str],
) -> tuple[AchievementUnlock, ...]:
    unlocks: list[AchievementUnlock] = []
    for definition in definitions_for_trigger(event.trigger):
        if definition.code in existing_codes:
            continue
        if definition.scope == "group" and event.telegram_chat_id is None:
            continue
        progress = snapshot.value(definition.metric)
        if not _matches(definition, progress):
            continue
        unlocks.append(
            AchievementUnlock(
                definition=definition,
                progress=progress,
                telegram_user_id=event.telegram_user_id,
                telegram_chat_id=(
                    event.telegram_chat_id if definition.scope == "group" else None
                ),
                occurred_at=event.occurred_at,
            )
        )
    return tuple(unlocks)
