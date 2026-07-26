from __future__ import annotations

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from app.api.rate_limit import enforce_rate_limit
from app.observability.metrics import Metrics
from app.operations.rate_limits import RateLimitDecision, RateLimitUnavailable


class FakeService:
    def __init__(self, result=None, error=None) -> None:
        self.result = result
        self.error = error

    async def check(self, policy: str, identity: str):
        if self.error:
            raise self.error
        return self.result


def request(*, service, production: bool, redis_required: bool):
    settings = SimpleNamespace(
        redis_required=redis_required,
        production=production,
        trust_proxy_headers=False,
    )
    app = SimpleNamespace(
        state=SimpleNamespace(
            settings=settings,
            rate_limit_service=service,
            metrics=Metrics.create(),
        )
    )
    return SimpleNamespace(app=app, headers={}, client=SimpleNamespace(host="127.0.0.1"))


async def test_optional_local_environment_bypasses_unavailable_protected_dependency() -> None:
    current = request(
        service=FakeService(error=RateLimitUnavailable()),
        production=False,
        redis_required=False,
    )
    await enforce_rate_limit(current, "billing", "123")


async def test_production_protected_operation_fails_closed_when_redis_is_unavailable() -> None:
    current = request(
        service=FakeService(error=RateLimitUnavailable()),
        production=True,
        redis_required=True,
    )
    with pytest.raises(HTTPException) as caught:
        await enforce_rate_limit(current, "billing", "123")
    assert caught.value.status_code == 503
    assert caught.value.detail["code"] == "OPERATIONAL_DEPENDENCY_UNAVAILABLE"


async def test_rejected_request_has_stable_error_and_retry_after() -> None:
    current = request(
        service=FakeService(result=RateLimitDecision(False, 0, 4)),
        production=True,
        redis_required=True,
    )
    with pytest.raises(HTTPException) as caught:
        await enforce_rate_limit(current, "billing", "123")
    assert caught.value.status_code == 429
    assert caught.value.detail["code"] == "RATE_LIMITED"
    assert caught.value.headers == {"Retry-After": "4"}
