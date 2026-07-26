from typing import Literal

from pydantic import BaseModel, ConfigDict

from app.services.vip_plans import VIPPlanCode


class CreateInvoiceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plan_code: VIPPlanCode


class SubscriptionUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    canceled: bool


ExportPeriod = Literal["week", "month", "all"]
