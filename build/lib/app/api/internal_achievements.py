import hmac

from fastapi import APIRouter, Header, HTTPException, Request, status

from app.services.achievement_backfill import AchievementBackfillService

router = APIRouter(tags=["internal"])


@router.post("/internal/achievement-backfill")
async def achievement_backfill(
    request: Request,
    scheduler_secret: str | None = Header(
        default=None,
        alias="X-ChatPulse-Scheduler-Secret",
    ),
) -> dict[str, int | bool]:
    expected_secret = request.app.state.settings.scheduler_secret
    if not expected_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Scheduler secret is not configured",
        )
    if scheduler_secret is None or not hmac.compare_digest(
        scheduler_secret,
        expected_secret,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid scheduler secret",
        )

    service = AchievementBackfillService(
        request.app.state.database.session_factory,
    )
    result = await service.run()
    return {"ok": True, **result}
