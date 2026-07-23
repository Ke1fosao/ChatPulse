from datetime import UTC, datetime, timedelta

import pytest

from app.database import Database
from app.models import User
from app.repositories.billing import BillingRepository


@pytest.fixture
async def billing(tmp_path):
    database = Database(f"sqlite+aiosqlite:///{tmp_path / 'billing.db'}")
    await database.create_schema()
    async with database.session_factory() as session, session.begin():
        session.add_all(
            [
                User(telegram_id=202, username="trial", first_name="Trial"),
                User(telegram_id=303, username="subscriber", first_name="Subscriber"),
            ]
        )
    yield BillingRepository(database.session_factory)
    await database.dispose()


@pytest.mark.asyncio
async def test_trial_invoice_is_validated_and_grants_exactly_seven_days(billing) -> None:
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    invoice = await billing.create_invoice_intent(202, "trial_7d", now=now)

    assert invoice["stars"] == 1
    assert invoice["recurring"] is False
    assert await billing.validate_checkout(
        user_id=202,
        payload=invoice["payload"],
        currency="XTR",
        total_amount=1,
        now=now,
    ) == (True, "")

    result = await billing.record_payment(
        user_id=202,
        payload=invoice["payload"],
        currency="XTR",
        total_amount=1,
        telegram_payment_charge_id="trial-charge",
        provider_payment_charge_id=None,
        is_recurring=False,
        is_first_recurring=False,
        subscription_expiration_date=None,
        now=now,
    )

    assert result.status == "granted"
    assert result.expires_at == now + timedelta(days=7)
    assert await billing.trial_available(202, now=now) is False
    status = await billing.get_status(202, now=now)
    assert status["is_vip"] is True
    assert status["trial_available"] is False


@pytest.mark.asyncio
async def test_successful_charge_is_idempotent_and_does_not_extend_twice(billing) -> None:
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    invoice = await billing.create_invoice_intent(202, "quarter_90d", now=now)
    arguments = {
        "user_id": 202,
        "payload": invoice["payload"],
        "currency": "XTR",
        "total_amount": 149,
        "telegram_payment_charge_id": "same-charge",
        "provider_payment_charge_id": None,
        "is_recurring": False,
        "is_first_recurring": False,
        "subscription_expiration_date": None,
        "now": now,
    }

    first = await billing.record_payment(**arguments)
    second = await billing.record_payment(**arguments)

    assert first.status == "granted"
    assert second.status == "duplicate"
    assert second.payment_id == first.payment_id
    assert second.expires_at == first.expires_at == now + timedelta(days=90)
    assert len(await billing.list_history(202)) == 1


@pytest.mark.asyncio
async def test_one_time_plans_stack_from_current_paid_expiry(billing) -> None:
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    first_invoice = await billing.create_invoice_intent(202, "quarter_90d", now=now)
    first = await billing.record_payment(
        user_id=202,
        payload=first_invoice["payload"],
        currency="XTR",
        total_amount=149,
        telegram_payment_charge_id="quarter-charge",
        provider_payment_charge_id=None,
        is_recurring=False,
        is_first_recurring=False,
        subscription_expiration_date=None,
        now=now,
    )
    year_invoice = await billing.create_invoice_intent(202, "year_365d", now=now)
    year = await billing.record_payment(
        user_id=202,
        payload=year_invoice["payload"],
        currency="XTR",
        total_amount=499,
        telegram_payment_charge_id="year-charge",
        provider_payment_charge_id=None,
        is_recurring=False,
        is_first_recurring=False,
        subscription_expiration_date=None,
        now=now,
    )

    assert first.expires_at == now + timedelta(days=90)
    assert year.expires_at == now + timedelta(days=455)


@pytest.mark.asyncio
async def test_two_open_trial_invoices_only_grant_first_and_require_second_refund(billing) -> None:
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    first_invoice = await billing.create_invoice_intent(202, "trial_7d", now=now)
    second_invoice = await billing.create_invoice_intent(202, "trial_7d", now=now)

    first = await billing.record_payment(
        user_id=202,
        payload=first_invoice["payload"],
        currency="XTR",
        total_amount=1,
        telegram_payment_charge_id="first-trial",
        provider_payment_charge_id=None,
        is_recurring=False,
        is_first_recurring=False,
        subscription_expiration_date=None,
        now=now,
    )
    duplicate = await billing.record_payment(
        user_id=202,
        payload=second_invoice["payload"],
        currency="XTR",
        total_amount=1,
        telegram_payment_charge_id="second-trial",
        provider_payment_charge_id=None,
        is_recurring=False,
        is_first_recurring=False,
        subscription_expiration_date=None,
        now=now,
    )

    assert first.status == "granted"
    assert duplicate.status == "duplicate_trial"
    assert duplicate.refund_required is True
    assert duplicate.expires_at is None
    status = await billing.get_status(202, now=now)
    assert status["vip_expires_at"] == (now + timedelta(days=7)).isoformat()


@pytest.mark.asyncio
async def test_monthly_plan_uses_telegram_subscription_expiry(billing) -> None:
    now = datetime(2026, 7, 23, 12, 0, tzinfo=UTC)
    expiry = now + timedelta(days=30)
    invoice = await billing.create_invoice_intent(303, "monthly_30d", now=now)

    result = await billing.record_payment(
        user_id=303,
        payload=invoice["payload"],
        currency="XTR",
        total_amount=59,
        telegram_payment_charge_id="subscription-charge",
        provider_payment_charge_id=None,
        is_recurring=True,
        is_first_recurring=True,
        subscription_expiration_date=int(expiry.timestamp()),
        now=now,
    )

    assert result.expires_at == expiry
    status = await billing.get_status(303, now=now)
    assert status["active_subscription"] == {
        "product_code": "monthly_30d",
        "expires_at": expiry.isoformat(),
        "is_canceled": False,
    }
    control = await billing.get_subscription_control(303)
    assert control is not None
    assert control["telegram_payment_charge_id"] == "subscription-charge"


@pytest.mark.asyncio
async def test_checkout_rejects_wrong_user_currency_and_amount(billing) -> None:
    invoice = await billing.create_invoice_intent(202, "quarter_90d")

    wrong_user = await billing.validate_checkout(
        user_id=303,
        payload=invoice["payload"],
        currency="XTR",
        total_amount=149,
    )
    wrong_currency = await billing.validate_checkout(
        user_id=202,
        payload=invoice["payload"],
        currency="USD",
        total_amount=149,
    )
    wrong_amount = await billing.validate_checkout(
        user_id=202,
        payload=invoice["payload"],
        currency="XTR",
        total_amount=1,
    )

    assert wrong_user[0] is False
    assert wrong_currency[0] is False
    assert wrong_amount[0] is False
