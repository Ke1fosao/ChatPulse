from __future__ import annotations

import secrets
from dataclasses import asdict, dataclass
from typing import Literal

VIPPlanCode = Literal["trial_7d", "monthly_30d", "quarter_90d", "year_365d"]
MONTH_SECONDS = 30 * 24 * 60 * 60


@dataclass(frozen=True, slots=True)
class VIPPlan:
    code: VIPPlanCode
    title: str
    short_title: str
    description: str
    stars: int
    duration_days: int
    recurring: bool = False
    badge: str | None = None

    @property
    def subscription_period(self) -> int | None:
        return MONTH_SECONDS if self.recurring else None

    def to_public_dict(self, *, available: bool = True) -> dict:
        payload = asdict(self)
        payload["subscription_period"] = self.subscription_period
        payload["available"] = available
        return payload


VIP_PLANS: dict[VIPPlanCode, VIPPlan] = {
    "trial_7d": VIPPlan(
        code="trial_7d",
        title="Спробувати VIP",
        short_title="7 днів",
        description="Повний VIP на 7 днів. Лише один раз і без автопродовження.",
        stars=1,
        duration_days=7,
        badge="ПЕРШИЙ РАЗ",
    ),
    "monthly_30d": VIPPlan(
        code="monthly_30d",
        title="VIP на місяць",
        short_title="30 днів",
        description="Автоматичне продовження кожні 30 днів. Можна вимкнути будь-коли.",
        stars=59,
        duration_days=30,
        recurring=True,
        badge="ПОПУЛЯРНИЙ",
    ),
    "quarter_90d": VIPPlan(
        code="quarter_90d",
        title="VIP на 3 місяці",
        short_title="90 днів",
        description="Разова покупка без автоматичного продовження.",
        stars=149,
        duration_days=90,
        badge="ВИГІДНО",
    ),
    "year_365d": VIPPlan(
        code="year_365d",
        title="VIP на рік",
        short_title="365 днів",
        description="Найнижча ціна за місяць. Разова покупка.",
        stars=499,
        duration_days=365,
        badge="НАЙКРАЩА ЦІНА",
    ),
}

VIP_BENEFITS = (
    "Повна історія та розширені порівняння",
    "Преміальні теми звітів і профілю",
    "CSV та PDF-експорт аналітики",
    "Розширені сповіщення про VIP і платежі",
    "Три закріплені досягнення у профілі",
    "VIP-бейдж без переваг у XP та рейтингах",
)


def get_vip_plan(code: str) -> VIPPlan:
    try:
        return VIP_PLANS[code]  # type: ignore[index]
    except KeyError as error:
        raise LookupError("Unknown VIP plan") from error


def new_invoice_payload(code: VIPPlanCode) -> str:
    return f"chatpulse-vip:{code}:{secrets.token_urlsafe(24)}"
