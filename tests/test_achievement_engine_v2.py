from datetime import UTC, datetime

from app.achievements.catalog import (
    ACHIEVEMENT_BY_CODE,
    ACHIEVEMENTS,
    AchievementRarity,
    definitions_for_trigger,
)
from app.achievements.engine import AchievementEvent, AchievementSnapshot, evaluate_event

LEGACY_CODES = {
    "first_steps",
    "level_5",
    "messages_100",
    "messages_1000",
    "reactions_100",
    "replies_100",
    "photos_50",
    "voices_25",
    "streak_7",
    "streak_30",
}


def test_catalog_is_large_unique_and_legacy_compatible() -> None:
    assert len(ACHIEVEMENTS) >= 65
    assert len(ACHIEVEMENT_BY_CODE) == len(ACHIEVEMENTS)
    assert LEGACY_CODES <= set(ACHIEVEMENT_BY_CODE)
    assert {item.rarity for item in ACHIEVEMENTS} == set(AchievementRarity)


def test_chain_stages_are_contiguous() -> None:
    chains: dict[str, list[int]] = {}
    totals: dict[str, int] = {}
    for item in ACHIEVEMENTS:
        if item.chain_key is None:
            continue
        chains.setdefault(item.chain_key, []).append(item.chain_stage)
        totals[item.chain_key] = item.chain_total

    for key, stages in chains.items():
        assert sorted(stages) == list(range(1, totals[key] + 1)), key


def test_event_evaluation_only_checks_matching_trigger() -> None:
    snapshot = AchievementSnapshot(
        values={
            "messages_count": 120,
            "replies_count": 0,
            "xp_total": 500,
        }
    )
    event = AchievementEvent(
        trigger="message_created",
        telegram_user_id=101,
        telegram_chat_id=-1001,
        occurred_at=datetime.now(UTC),
    )

    unlocks = evaluate_event(event, snapshot, existing_codes=set())
    codes = {item.code for item in unlocks}

    assert "messages_100" in codes
    assert "replies_100" not in codes
    assert all(item.definition.trigger == "message_created" for item in unlocks)


def test_existing_unlocks_are_never_returned_twice() -> None:
    event = AchievementEvent(
        trigger="streak_updated",
        telegram_user_id=101,
        telegram_chat_id=-1001,
        occurred_at=datetime.now(UTC),
    )
    snapshot = AchievementSnapshot(values={"current_streak": 30})

    unlocks = evaluate_event(event, snapshot, existing_codes={"streak_7"})
    codes = {item.code for item in unlocks}

    assert "streak_7" not in codes
    assert "streak_30" in codes


def test_secret_definition_masks_locked_payload() -> None:
    secret = next(item for item in ACHIEVEMENTS if item.hidden)

    masked = secret.to_public_dict(earned=False, progress=secret.threshold - 1)
    revealed = secret.to_public_dict(earned=True, progress=secret.threshold)

    assert masked["title"] == "???"
    assert masked["description"] == "Секретне досягнення"
    assert masked["progress"] == 0
    assert masked["threshold"] == 0
    assert revealed["title"] == secret.title
    assert revealed["threshold"] == secret.threshold


def test_inverse_ranking_payload_keeps_actual_rank_and_comparator() -> None:
    rank_one = ACHIEVEMENT_BY_CODE["rank_1"]

    payload = rank_one.to_public_dict(earned=False, progress=3)

    assert payload["progress"] == 3
    assert payload["threshold"] == 1
    assert payload["comparator"] == "lte"


def test_trigger_lookup_is_indexed_and_stable() -> None:
    definitions = definitions_for_trigger("reaction_received")

    assert definitions
    assert all(item.trigger == "reaction_received" for item in definitions)
    assert definitions == definitions_for_trigger("reaction_received")
