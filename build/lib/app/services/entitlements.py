from dataclasses import asdict, dataclass
from datetime import UTC, datetime

PREMIUM_ENTITLEMENTS = (
    "analytics.extended_history",
    "analytics.advanced_compare",
    "reports.premium_themes",
    "reports.export_csv",
    "reports.export_pdf",
    "reports.ai_insights",
    "notifications.advanced",
    "profile.premium_card",
    "premium.all",
)


@dataclass(frozen=True, slots=True)
class AccountAccess:
    plan: str
    is_owner: bool
    is_vip: bool
    vip_expires_at: datetime | None
    entitlements: tuple[str, ...]

    def to_dict(self) -> dict:
        payload = asdict(self)
        payload["vip_expires_at"] = (
            self.vip_expires_at.astimezone(UTC).isoformat() if self.vip_expires_at else None
        )
        payload["entitlements"] = list(self.entitlements)
        return payload


def build_account_access(
    *,
    is_owner: bool,
    vip_is_active: bool,
    vip_expires_at: datetime | None,
    now: datetime | None = None,
) -> AccountAccess:
    current = now or datetime.now(UTC)
    if current.tzinfo is None:
        current = current.replace(tzinfo=UTC)
    current = current.astimezone(UTC)

    expires_at = vip_expires_at
    if expires_at is not None:
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        expires_at = expires_at.astimezone(UTC)

    if is_owner:
        return AccountAccess(
            plan="owner",
            is_owner=True,
            is_vip=False,
            vip_expires_at=None,
            entitlements=PREMIUM_ENTITLEMENTS,
        )

    active_vip = vip_is_active and (expires_at is None or expires_at > current)
    if active_vip:
        return AccountAccess(
            plan="vip",
            is_owner=False,
            is_vip=True,
            vip_expires_at=expires_at,
            entitlements=PREMIUM_ENTITLEMENTS,
        )

    return AccountAccess(
        plan="free",
        is_owner=False,
        is_vip=False,
        vip_expires_at=None,
        entitlements=(),
    )
