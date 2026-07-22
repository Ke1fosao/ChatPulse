from datetime import UTC, datetime, timedelta

from app.services.entitlements import PREMIUM_ENTITLEMENTS, build_account_access


def test_free_user_has_no_premium_entitlements() -> None:
    now = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)

    access = build_account_access(
        is_owner=False,
        vip_is_active=False,
        vip_expires_at=None,
        now=now,
    )

    assert access.plan == "free"
    assert access.is_owner is False
    assert access.is_vip is False
    assert access.entitlements == ()


def test_active_vip_receives_every_premium_entitlement() -> None:
    now = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)

    access = build_account_access(
        is_owner=False,
        vip_is_active=True,
        vip_expires_at=now + timedelta(days=30),
        now=now,
    )

    assert access.plan == "vip"
    assert access.is_vip is True
    assert access.entitlements == PREMIUM_ENTITLEMENTS


def test_expired_vip_falls_back_to_free() -> None:
    now = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)

    access = build_account_access(
        is_owner=False,
        vip_is_active=True,
        vip_expires_at=now - timedelta(seconds=1),
        now=now,
    )

    assert access.plan == "free"
    assert access.is_vip is False
    assert access.entitlements == ()


def test_owner_always_has_every_premium_entitlement_without_becoming_vip() -> None:
    now = datetime(2026, 7, 22, 10, 0, tzinfo=UTC)

    access = build_account_access(
        is_owner=True,
        vip_is_active=False,
        vip_expires_at=None,
        now=now,
    )

    assert access.plan == "owner"
    assert access.is_owner is True
    assert access.is_vip is False
    assert access.entitlements == PREMIUM_ENTITLEMENTS
