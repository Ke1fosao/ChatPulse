from app.services.entitlements import AccountAccess

FREE_REPORT_THEMES = {"dark_pulse"}
PREMIUM_REPORT_THEMES = {"telegram_wave", "clean_light", "aurora_gold"}
ALL_REPORT_THEMES = FREE_REPORT_THEMES | PREMIUM_REPORT_THEMES


def has_entitlement(account: AccountAccess, entitlement: str) -> bool:
    return bool(
        account.is_owner
        or "premium.all" in account.entitlements
        or entitlement in account.entitlements
    )


def require_report_theme_access(account: AccountAccess, theme: str) -> None:
    if theme not in ALL_REPORT_THEMES:
        raise ValueError("Unsupported report theme")
    if theme in PREMIUM_REPORT_THEMES and not has_entitlement(account, "reports.premium_themes"):
        raise PermissionError("Ця тема доступна у ChatPulse VIP.")
