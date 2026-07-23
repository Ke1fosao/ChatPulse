import pytest

from app.services.entitlements import build_account_access
from app.services.premium_policy import require_report_theme_access


def test_default_theme_remains_free() -> None:
    account = build_account_access(is_owner=False, vip_is_active=False, vip_expires_at=None)
    require_report_theme_access(account, "dark_pulse")


def test_premium_themes_require_vip() -> None:
    account = build_account_access(is_owner=False, vip_is_active=False, vip_expires_at=None)
    with pytest.raises(PermissionError, match="VIP"):
        require_report_theme_access(account, "telegram_wave")


def test_vip_and_owner_can_use_premium_themes() -> None:
    vip = build_account_access(is_owner=False, vip_is_active=True, vip_expires_at=None)
    owner = build_account_access(is_owner=True, vip_is_active=False, vip_expires_at=None)

    require_report_theme_access(vip, "clean_light")
    require_report_theme_access(owner, "aurora_gold")
