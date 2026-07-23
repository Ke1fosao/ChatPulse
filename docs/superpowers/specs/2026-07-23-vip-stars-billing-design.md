# ChatPulse VIP Stars Billing Design

## Goal

Add a safe, inexpensive VIP purchase flow inside the Telegram Mini App using Telegram Stars, without changing the fairness of XP or rankings.

## Products

- `trial_7d`: 7 days, 1 Star, one successful use per Telegram user, one-time invoice, no automatic renewal.
- `monthly_30d`: 30-day recurring Telegram Stars subscription, 59 Stars per period.
- `quarter_90d`: 90 days, 149 Stars, one-time invoice.
- `year_365d`: 365 days, 499 Stars, one-time invoice.

The trial is available only when the user has never completed a Stars VIP payment, has not claimed the trial, and does not currently have active VIP. Multiple trial invoice links may exist, but only the first successful payment may claim the trial. Any later duplicate trial payment is automatically refunded.

## Architecture

Billing is isolated from analytics and gamification:

- `app/services/vip_plans.py` defines immutable products, public plan payloads, invoice payload generation and duration rules.
- `app/billing_models.py` stores invoice intents, successful payments and one-time trial claims.
- `app/repositories/billing.py` validates checkout, records payments idempotently and extends `VipGrant` atomically.
- `app/api/billing/routes.py` exposes authenticated Mini App endpoints for plans, invoice links, account billing status, purchase history, exports and subscription cancellation.
- `app/bot/routers/payments.py` handles `pre_checkout_query`, `successful_payment` and duplicate-trial refunds.
- `/miniapp/vip` is a dedicated React screen with plan cards, benefits, purchase history and active subscription controls.

## Payment flow

1. Mini App requests a product invoice.
2. Backend verifies the current Telegram user and product eligibility.
3. Backend creates a random invoice payload and persists an invoice intent.
4. Backend asks Telegram Bot API for an invoice link using currency `XTR`.
5. Mini App opens the invoice through `Telegram.WebApp.openInvoice`.
6. Bot accepts `pre_checkout_query` only when user, amount, currency and pending invoice match.
7. VIP is granted only after `successful_payment`.
8. `telegram_payment_charge_id` is stored uniquely for idempotency and refunds.

For the monthly plan, the Telegram-provided `subscription_expiration_date` is the VIP expiry. For one-time plans, time is added from the later of now or the current VIP expiry, so purchases stack instead of deleting already paid time.

## VIP benefits in this release

- premium report-card themes;
- CSV and image-based PDF exports for group analytics;
- premium profile-card status and visuals already supported by the profile renderer;
- three featured achievements in the profile data model and API;
- extended billing history and subscription controls;
- VIP badge and clear expiry information.

AI insights are explicitly excluded from this release.

VIP never receives extra XP, ranking multipliers, free streak progress or any competitive advantage.

## Security and correctness

- Telegram identity comes only from verified Mini App `initData` or verified payment updates.
- The frontend never supplies a price, duration or VIP expiry.
- Invoice payloads are random, server-persisted and bound to a Telegram user.
- Checkout verifies `XTR`, exact amount and exact user.
- Successful charges are unique and idempotent.
- Trial claims have a database primary key on Telegram user ID.
- Duplicate trial charges are recorded as refunded and refunded through Telegram.
- Direct Supabase `anon` and `authenticated` access to billing tables is revoked and RLS is enabled.

## Error handling

- Ineligible trial: return HTTP 409 with a user-friendly message.
- Unknown or stale invoice: reject pre-checkout.
- Duplicate successful update: return the existing payment result without extending VIP twice.
- Duplicate trial payment: refund automatically and do not extend VIP.
- Telegram invoice-link failure: keep the intent invalidated and return HTTP 502.
- Subscription cancellation: cancel future renewal only; VIP stays active until the current expiration date.

## Testing

Backend tests cover product prices, trial eligibility, invoice validation, idempotent payments, stacking, recurring expiry, duplicate-trial handling, authenticated API access and payment router behavior.

Frontend tests cover plan rendering, trial visibility, invoice opening, successful refresh, error feedback and active subscription cancellation.

Full Ruff, pytest, compileall, Vitest, TypeScript, Vite and Docker checks must pass before merge.
