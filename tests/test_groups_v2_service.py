from datetime import UTC, date, datetime, timedelta

from app.services.groups_v2 import (
    build_group_insights,
    calculate_group_pulse,
    derive_group_status,
)


def test_group_status_boundaries_and_setup_priority() -> None:
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)

    assert derive_group_status(
        bot_operational=False,
        is_paused=False,
        last_activity_at=now,
        now=now,
    )["id"] == "needs_setup"
    assert derive_group_status(
        bot_operational=True,
        is_paused=True,
        last_activity_at=now,
        now=now,
    )["id"] == "needs_setup"
    assert derive_group_status(
        bot_operational=True,
        is_paused=False,
        last_activity_at=now - timedelta(hours=24),
        now=now,
    )["id"] == "active"
    assert derive_group_status(
        bot_operational=True,
        is_paused=False,
        last_activity_at=now - timedelta(days=7),
        now=now,
    )["id"] == "quiet"
    assert derive_group_status(
        bot_operational=True,
        is_paused=False,
        last_activity_at=now - timedelta(days=7, seconds=1),
        now=now,
    )["id"] == "inactive"


def test_group_pulse_is_clamped_and_explained() -> None:
    pulse = calculate_group_pulse(
        {
            "messages_count": 120,
            "active_members": 9,
            "reactions_received": 80,
            "replies_count": 30,
        },
        {"messages_count": 30},
        total_members=10,
        consecutive_active_days=10,
        period_days=7,
    )

    assert 0 <= pulse["score"] <= 100
    assert pulse["label"] == "Дуже активно"
    assert pulse["components"] == {
        "messages": 100,
        "members": 90,
        "engagement": 92,
        "continuity": 100,
    }
    assert "більше" in pulse["positive"]


def test_group_insights_are_private_safe_and_limited() -> None:
    insights = build_group_insights(
        rank_change=3,
        achievement_title="Перші кроки",
        record_messages=77,
        record_date=date(2026, 7, 22),
        consecutive_active_days=6,
        leader_name="Dmytro",
        report_ready=True,
    )

    assert len(insights) == 5
    assert insights[0]["id"] == "rank_up"
    assert all("message_text" not in item for item in insights)


def test_group_insights_have_a_neutral_fallback() -> None:
    assert build_group_insights()[0]["id"] == "steady"
