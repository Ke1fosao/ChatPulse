from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field

from app.api.miniapp.auth import TelegramMiniAppUser
from app.api.owner.dependencies import get_owner_user

router = APIRouter(prefix="/api/owner/v1/payments", tags=["owner-revenue"])


class OwnerPaymentNoteRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int
    text: str = Field(min_length=1, max_length=1000)


class OwnerRefundRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=5, max_length=255)
    confirmation: str = Field(min_length=1, max_length=80)


class OwnerSubscriptionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    user_id: int
    canceled: bool
    reason: str = Field(min_length=3, max_length=255)


def _repository(request: Request):
    return request.app.state.owner_revenue_repository


def _service(request: Request):
    return request.app.state.owner_payment_service


@router.get("/summary")
async def payment_summary(
    request: Request,
    _owner: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
    days: Annotated[int, Query(ge=1, le=366)] = 30,
) -> dict:
    return await _repository(request).get_summary(days=days)


@router.get("/timeline")
async def payment_timeline(
    request: Request,
    _owner: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
    days: Annotated[int, Query(ge=7, le=366)] = 30,
) -> dict:
    return {"items": await _repository(request).get_timeline(days=days)}


@router.get("/plans")
async def payment_plans(
    request: Request,
    _owner: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
    days: Annotated[int, Query(ge=1, le=366)] = 30,
) -> dict:
    return {"items": await _repository(request).get_plan_distribution(days=days)}


@router.get("/transactions")
async def transactions(
    request: Request,
    _owner: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
    q: Annotated[str | None, Query(max_length=128)] = None,
    product: Annotated[str | None, Query(max_length=32)] = None,
    payment_status: Annotated[
        Literal["paid", "refunded", "refund_required"] | None, Query()
    ] = None,
    recurring: Annotated[bool | None, Query()] = None,
    days: Annotated[int | None, Query(ge=1, le=366)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> dict:
    return await _repository(request).list_transactions(
        query=q,
        product_code=product,
        status=payment_status,
        recurring=recurring,
        days=days,
        limit=limit,
        offset=offset,
    )


@router.get("/transactions/{payment_id}")
async def transaction_detail(
    payment_id: int,
    request: Request,
    _owner: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
) -> dict:
    payload = await _repository(request).get_transaction(payment_id)
    if payload is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Payment not found")
    return payload


@router.put("/transactions/{payment_id}/note")
async def update_payment_note(
    payment_id: int,
    payload: OwnerPaymentNoteRequest,
    request: Request,
    owner: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
) -> dict:
    try:
        note = await _repository(request).save_note(
            owner_user_id=owner.telegram_id,
            payment_id=payment_id,
            user_id=payload.user_id,
            text=payload.text,
        )
        await _service(request).audit_note(
            owner_user_id=owner.telegram_id,
            payment_id=payment_id,
            user_id=payload.user_id,
        )
        return {"note": note}
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error


@router.post("/transactions/{payment_id}/refund")
async def refund_payment(
    payment_id: int,
    payload: OwnerRefundRequest,
    request: Request,
    owner: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
) -> dict:
    try:
        return await _service(request).refund(
            request.app.state.bot,
            owner_user_id=owner.telegram_id,
            payment_id=payment_id,
            reason=payload.reason,
            confirmation=payload.confirmation,
        )
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=str(error)) from error


@router.post("/subscription")
async def owner_subscription_state(
    payload: OwnerSubscriptionRequest,
    request: Request,
    owner: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
) -> dict:
    try:
        return await _service(request).set_subscription_state(
            request.app.state.bot,
            owner_user_id=owner.telegram_id,
            user_id=payload.user_id,
            canceled=payload.canceled,
            reason=payload.reason,
        )
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(error)
        ) from error


@router.get("/export.csv")
async def export_payments_csv(
    request: Request,
    _owner: Annotated[TelegramMiniAppUser, Depends(get_owner_user)],
    q: Annotated[str | None, Query(max_length=128)] = None,
    product: Annotated[str | None, Query(max_length=32)] = None,
    payment_status: Annotated[str | None, Query(max_length=24)] = None,
    recurring: Annotated[bool | None, Query()] = None,
    days: Annotated[int | None, Query(ge=1, le=366)] = None,
) -> Response:
    content = await _repository(request).export_csv(
        query=q,
        product_code=product,
        status=payment_status,
        recurring=recurring,
        days=days,
    )
    return Response(
        content=content,
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": "attachment; filename=chatpulse-payments.csv"},
    )
