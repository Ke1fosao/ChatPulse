import pytest

from app.domain import MessageActivity
from app.services.gamification import (
    adjusted_message_xp,
    content_fingerprints,
    format_comparison,
    hamming_distance,
    level_for_xp,
    level_tier,
    message_base_xp,
    parse_report_time,
    xp_threshold_for_level,
)


def test_weighted_message_xp() -> None:
    assert (
        message_base_xp(
            MessageActivity(
                is_media=True,
                is_reply=True,
                is_photo=True,
                has_qualifying_text=True,
            )
        )
        == 5
    )
    assert message_base_xp(MessageActivity(is_media=True, is_reply=False)) == 0


def test_burst_reduction_is_strict() -> None:
    assert adjusted_message_xp(5, 20) == 5
    assert adjusted_message_xp(5, 21) == 2
    assert adjusted_message_xp(5, 31) == 1
    assert adjusted_message_xp(5, 41) == 0


def test_level_thresholds_are_stable() -> None:
    assert xp_threshold_for_level(1) == 0
    assert xp_threshold_for_level(2) == 100
    assert xp_threshold_for_level(5) == 1000
    assert level_for_xp(99) == 1
    assert level_for_xp(100) == 2
    assert level_for_xp(1000) == 5
    assert level_tier(5) == "Бронза"
    assert level_tier(35) == "Діамант"


def test_keyed_fingerprints_detect_similarity_without_storing_text() -> None:
    first = content_fingerprints("Привіт світе", media_key=None, secret="secret")
    second = content_fingerprints("Привіт, світе!", media_key=None, secret="secret")
    other_secret = content_fingerprints("Привіт світе", media_key=None, secret="other")

    assert first[0] != "Привіт світе"
    assert first[0] != other_secret[0]
    assert first[1] is not None and second[1] is not None
    assert hamming_distance(first[1], second[1]) <= 3


def test_report_time_accepts_full_day() -> None:
    assert parse_report_time("00:00").hour == 0
    assert parse_report_time("23:59").minute == 59
    with pytest.raises(ValueError):
        parse_report_time("24:00")
    with pytest.raises(ValueError):
        parse_report_time("nine")


def test_comparison_contains_direction() -> None:
    text = format_comparison(
        {
            "messages_count": 20,
            "reactions_received": 10,
            "active_members": 4,
            "photo_count": 2,
            "voice_count": 1,
        },
        {
            "messages_count": 10,
            "reactions_received": 5,
            "active_members": 2,
            "photo_count": 1,
            "voice_count": 0,
        },
    )
    assert "10 → 20" in text
    assert "стала активнішою" in text
