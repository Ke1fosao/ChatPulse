from __future__ import annotations

from fastapi import HTTPException, Request, status

from app.operations.rate_limits import POLICIES, RateLimitService, RateLimitUnavailable

_RATE_LIMITED = {
    "code": "RATE_LIMITED",
    "message": "Забагато запитів. Спробуйте трохи пізніше.",
}
_DEPENDENCY_UNAVAILABLE = {
    "code": "OPERATIONAL_DEPENDENCY_UNAVAILABLE",
    "message": "Операція тимчасово недоступна.",
}


def remote_address(request: Request) -> str:
    settings = request.app.state.settings
    if settings.trust_proxy_headers:
        forwarded = request.headers.get("x-forwarded-for", "")
        candidate = forwarded.split(",", 1)[0].strip()
        if candidate:
            return candidate
    return request.client.host if request.client else "unknown"


def _may_bypass_unavailable_dependency(request: Request, *, fail_open: bool) -> bool:
    settings = request.app.state.settings
    return fail_open or (not settings.redis_required and not settings.production)


async def enforce_rate_limit(request: Request, policy: str, identity: str) -> None:
    service: RateLimitService | None = getattr(request.app.state, "rate_limit_service", None)
    selected = POLICIES[policy]
    if service is None:
        if _may_bypass_unavailable_dependency(request, fail_open=selected.fail_open):
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_DEPENDENCY_UNAVAILABLE,
        )
    try:
        decision = await service.check(policy, identity)
    except RateLimitUnavailable as error:
        metrics = getattr(request.app.state, "metrics", None)
        if metrics is not None:
            metrics.rate_limits.labels(policy=policy, outcome="unavailable").inc()
        if _may_bypass_unavailable_dependency(request, fail_open=selected.fail_open):
            return
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=_DEPENDENCY_UNAVAILABLE,
        ) from error

    metrics = getattr(request.app.state, "metrics", None)
    if metrics is not None:
        metrics.rate_limits.labels(
            policy=policy,
            outcome="allowed" if decision.allowed else "rejected",
        ).inc()
    if decision.allowed:
        return
    retry_after = max(1, decision.retry_after_seconds)
    raise HTTPException(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        detail=_RATE_LIMITED,
        headers={"Retry-After": str(retry_after)},
    )
