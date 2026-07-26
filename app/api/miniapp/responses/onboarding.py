from __future__ import annotations

from typing import Any

from app.api.miniapp.responses.common import StrictResponse


class OnboardingResponse(StrictResponse):
    completed_steps: int
    total_steps: int
    is_complete: bool
    primary_action: str
    add_group_url: str | None = None
    linked_group: dict[str, Any] | None = None
    steps: list[dict[str, Any]]
