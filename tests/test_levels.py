from app.services.levels import MAX_LEVEL, build_level_catalog


def test_level_catalog_marks_current_unlocked_and_future_levels() -> None:
    payload = build_level_catalog(current_level=5, xp_total=1000)

    assert payload["max_level"] == MAX_LEVEL
    assert len(payload["levels"]) == MAX_LEVEL
    assert payload["levels"][0]["xp_required"] == 0
    assert payload["levels"][4]["is_current"] is True
    assert payload["levels"][4]["tier"] == "Бронза"
    assert payload["levels"][3]["is_unlocked"] is True
    assert payload["levels"][5]["is_unlocked"] is False
    assert payload["levels"][-1]["xp_to_next"] is None


def test_level_catalog_exposes_rewards_only_when_tier_changes() -> None:
    payload = build_level_catalog(current_level=1, xp_total=0)
    levels = payload["levels"]

    assert levels[0]["rewards"]
    assert levels[1]["rewards"] == []
    assert levels[4]["rewards"]
    assert levels[9]["rewards"]
    assert levels[19]["rewards"]
    assert levels[34]["rewards"]
