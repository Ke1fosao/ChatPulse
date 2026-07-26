from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict


class StrictResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")


class OkResponse(StrictResponse):
    ok: bool = True


class AccountAccessResponse(StrictResponse):
    plan: str
    is_owner: bool
    is_vip: bool
    vip_expires_at: str | None = None
    entitlements: list[str]


class CapabilitiesResponse(StrictResponse):
    is_admin: bool


class GenericItemsResponse(StrictResponse):
    items: list[dict[str, Any]]
