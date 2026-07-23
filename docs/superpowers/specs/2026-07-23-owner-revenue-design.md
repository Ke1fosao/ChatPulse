# ChatPulse Owner Revenue — Payments Analytics Design

Date: 2026-07-23
Status: Proposed for implementation

## Goal

Add a protected `Оплати` section to Owner Panel so the founder can understand revenue, subscriptions, trial conversion, refunds, and individual payment history without direct database access.

The existing owner security boundary remains unchanged: immutable Telegram owner ID, verified Mini App initData, server-side owner dependency, and audited mutations.

## Scope

Included:

- revenue KPI dashboard;
- payment and subscription charts;
- searchable transaction table;
- trial conversion funnel;
- user payment detail drawer;
- CSV export;
- controlled refunds;
- owner notes on payments or users;
- subscription cancellation/restoration;
- audit log entries for every financial mutation.

Excluded:

- multi-owner roles;
- accounting in fiat currency;
- tax calculations;
- withdrawal automation;
- referral analytics;
- promo-code analytics;
- arbitrary SQL access.

## Navigation

Add `payments` to `OwnerTab` and a fifth bottom-navigation item:

- label: `Оплати`;
- icon: wallet or star;
- route remains inside `/miniapp/owner` using the existing owner shell state.

On small screens, the navigation must remain readable and horizontally safe.

## Revenue overview

Top KPI cards:

- Stars earned today;
- Stars earned in the last 7 days;
- Stars earned in the last 30 days;
- Stars earned all time;
- successful payments in the selected period;
- active paid VIP users;
- active owner-granted VIP users;
- active monthly subscriptions;
- refunds count and refunded Stars;
- VIP users expiring in the next 7 days.

Definitions:

- revenue includes payments with status `paid` and excludes refunded or refund-required payments;
- paid VIP means the current active grant is backed by at least one successful non-refunded payment;
- gifted VIP means the active grant was issued by owner action and has no active paid entitlement;
- MRR is the sum of Stars for active non-canceled monthly subscriptions;
- ARPPU is successful non-refunded Stars divided by unique paying users in the period.

## Time controls

Global period selector:

- today;
- 7 days;
- 30 days;
- 90 days;
- all time;
- custom date range with a maximum span of 366 days.

The selected period applies to KPIs, charts, funnel, and export. Active-subscription counts always represent current state and are labeled accordingly.

## Charts

### Revenue timeline

Daily buckets with:

- gross Stars;
- refunded Stars;
- net Stars;
- successful payment count.

### Plan distribution

Shows payments and Stars by:

- 7-day trial;
- monthly;
- quarterly;
- yearly.

### New vs repeat buyers

Daily or weekly buckets based on selected range.

- new buyer: first successful payment in lifetime occurs inside the bucket;
- repeat buyer: successful payment after the first lifetime payment.

### Subscription state

Current totals:

- active auto-renew;
- canceled but still valid until period end;
- expired;
- renewal problem detected.

## Trial conversion funnel

Stages:

1. users who viewed a trial placement;
2. users who selected the trial plan;
3. users who opened a trial invoice;
4. users who paid 1 Star;
5. trial users who later bought any full-price plan;
6. trial users who bought monthly, quarterly, or yearly.

Metrics:

- view-to-invoice conversion;
- invoice-to-trial conversion;
- trial-to-paid conversion;
- median hours from trial start to paid purchase;
- preferred first full-price plan.

The funnel uses privacy-safe VIP analytics events and payment records. No message content is involved.

## Transaction table

Columns:

- payment date;
- user display name and username;
- Telegram user ID;
- plan;
- Stars;
- status;
- recurring or one-time;
- first recurring payment marker;
- VIP granted-until date;
- refund date when applicable;
- shortened Telegram charge ID.

Filters:

- text search by display name, username, Telegram ID, or charge ID;
- period;
- plan;
- status;
- recurring/one-time;
- first purchase/repeat purchase;
- trial/full-price;
- refunded/not refunded.

Pagination is server-side. Default page size is 50 and maximum is 100.

## Payment detail drawer

Opening a transaction shows:

- full payment metadata;
- current user VIP status;
- complete payment history for that user;
- owner VIP grant history;
- subscription state;
- refund state;
- owner notes;
- related audit entries.

Actions:

- open user in the existing owner user view;
- grant additional VIP time;
- cancel or restore monthly auto-renew;
- refund eligible payment;
- add or edit an internal note;
- copy Telegram user ID or charge ID.

## Refund flow

Telegram Bot API currently supports `refundStarPayment(user_id, telegram_payment_charge_id)` for successful Stars payments. The refund action must be server-only and owner-only.

Eligibility:

- payment status is `paid`;
- payment has not already been refunded;
- Telegram charge ID is present;
- user exists;
- owner enters a reason of at least 5 characters;
- owner enters the confirmation phrase `ПОВЕРНУТИ <amount> STARS`.

Execution order:

1. verify owner and payment eligibility;
2. create a pending audit entry;
3. call Telegram refund method;
4. on success, mark payment `refunded` with timestamp and reason;
5. recalculate paid VIP entitlement without removing unrelated paid time or owner-granted time;
6. send idempotent refund notification to the user;
7. finalize audit metadata.

Failure handling:

- Telegram failure leaves payment unchanged;
- audit entry records failure category without leaking secrets;
- UI shows a clear retryable or non-retryable error;
- duplicate refund requests are idempotent.

## Subscription control

Telegram Bot API supports canceling or re-enabling Stars subscription extension using the original subscription charge ID.

Owner action requires:

- current subscription record;
- confirmation dialog;
- reason;
- audited call to Telegram;
- local subscription-state update only after Telegram success.

Canceling auto-renew does not immediately remove VIP. Access remains active until the current paid expiration date.

## Owner notes

Add `owner_payment_notes` table:

- id;
- owner Telegram ID;
- payment ID nullable;
- user Telegram ID;
- note text limited to 1000 characters;
- created and updated timestamps.

Notes are private to Owner Panel, protected by RLS, and never exposed to the user-facing Mini App.

## Backend architecture

Add a focused `OwnerRevenueRepository` rather than expanding `OwnerPanelRepository` indefinitely.

Responsibilities:

- aggregate KPIs;
- build chart series;
- compute trial funnel;
- list and filter transactions;
- return payment detail;
- save notes;
- coordinate refund and subscription mutations through a service layer.

Add `OwnerPaymentService` for Telegram side effects:

- refund payment;
- cancel or restore subscription;
- entitlement recalculation;
- notification and audit coordination.

This keeps queries separate from external side effects.

## API design

All routes are under `/api/owner/v1/payments` and use `get_owner_user`.

Read endpoints:

- `GET /summary`;
- `GET /timeline`;
- `GET /plans`;
- `GET /funnel`;
- `GET /transactions`;
- `GET /transactions/{payment_id}`;
- `GET /export.csv`.

Mutation endpoints:

- `POST /transactions/{payment_id}/refund`;
- `POST /subscriptions/{payment_id}/state`;
- `PUT /transactions/{payment_id}/note`.

Request schemas forbid unknown fields. Date ranges and filters are validated server-side.

## Data model changes

Add:

- `vip_product_events` for conversion events;
- `owner_payment_notes` for private notes;
- optional explicit subscription state fields if current invoice intent status is insufficient;
- indexes for payment date, plan, status, user, and recurring state.

Existing billing tables remain the source of truth for invoices and payments.

All new tables:

- use foreign keys;
- enable RLS;
- revoke direct anonymous and authenticated client access;
- are accessed only by the backend service role or database connection.

## CSV export

Export matches the active filters and includes:

- payment date;
- user ID;
- username;
- plan;
- Stars;
- status;
- recurring flags;
- granted-until;
- refund date;
- charge ID.

The file excludes owner notes by default. A separate explicit option may include notes later.

## Audit requirements

Financial audit actions:

- `payment.refund_requested`;
- `payment.refunded`;
- `payment.refund_failed`;
- `subscription.canceled_by_owner`;
- `subscription.restored_by_owner`;
- `payment.note_updated`;
- `payments.csv_exported`.

Audit metadata includes IDs, plan, Stars, reason, and outcome. It never stores bot tokens or Telegram initData.

## Testing

Repository tests:

- KPI calculations with paid, refunded, trial, recurring, and gifted VIP data;
- MRR and ARPPU;
- new vs repeat classification;
- funnel conversion;
- filters and pagination;
- CSV export.

Service tests:

- successful refund;
- Telegram refund failure;
- duplicate refund idempotency;
- entitlement recalculation;
- subscription cancel and restore;
- notification idempotency;
- complete audit trail.

API tests:

- owner access only;
- invalid date ranges and filters;
- confirmation phrase enforcement;
- no financial mutation on Telegram failure.

Frontend tests:

- KPI and chart rendering;
- filters;
- transaction drawer;
- refund confirmation;
- error states;
- mobile navigation with five tabs.

## Rollout

Implement after the VIP distributed-experience PR. Apply the additive database migration before merging application code. Run backend, frontend, typecheck, production build, and Docker checks before merge.