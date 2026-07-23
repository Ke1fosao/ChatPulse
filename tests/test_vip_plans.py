import pytest

from app.services.vip_plans import MONTH_SECONDS, VIP_PLANS, get_vip_plan, new_invoice_payload


def test_vip_plan_prices_and_durations_are_fixed() -> None:
    assert {
        code: (plan.stars, plan.duration_days, plan.recurring)
        for code, plan in VIP_PLANS.items()
    } == {
        "trial_7d": (1, 7, False),
        "monthly_30d": (59, 30, True),
        "quarter_90d": (149, 90, False),
        "year_365d": (499, 365, False),
    }


def test_only_monthly_plan_has_telegram_subscription_period() -> None:
    assert VIP_PLANS["monthly_30d"].subscription_period == MONTH_SECONDS == 2_592_000
    assert VIP_PLANS["trial_7d"].subscription_period is None
    assert VIP_PLANS["quarter_90d"].subscription_period is None
    assert VIP_PLANS["year_365d"].subscription_period is None


def test_public_payload_never_accepts_client_price_or_duration() -> None:
    payload = VIP_PLANS["trial_7d"].to_public_dict(available=False)

    assert payload["stars"] == 1
    assert payload["duration_days"] == 7
    assert payload["available"] is False


def test_invoice_payload_is_unique_and_bound_to_product_code() -> None:
    first = new_invoice_payload("trial_7d")
    second = new_invoice_payload("trial_7d")

    assert first.startswith("chatpulse-vip:trial_7d:")
    assert second.startswith("chatpulse-vip:trial_7d:")
    assert first != second


def test_unknown_plan_is_rejected() -> None:
    with pytest.raises(LookupError, match="Unknown VIP plan"):
        get_vip_plan("made_up")
