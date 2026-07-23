# ChatPulse VIP Stars Billing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship Telegram Stars VIP purchases with a one-time 1-Star trial, recurring monthly plan, longer one-time plans, premium exports, featured achievements and subscription controls.

**Architecture:** A dedicated billing domain stores server-generated invoice intents and idempotent payment records, while the existing `VipGrant` remains the central entitlement source. Telegram payment updates activate VIP atomically; the Mini App opens invoice links and refreshes billing state after payment.

**Tech Stack:** Python 3.12, aiogram 3, FastAPI, SQLAlchemy 2 async, PostgreSQL/Supabase, React 19, TypeScript, Vite, Telegram Mini Apps and Telegram Stars.

## Global Constraints

- Prices are fixed server-side: 1, 59, 149 and 499 Telegram Stars.
- Trial is usable once per Telegram user and has no automatic renewal.
- Monthly subscription period is exactly 2592000 seconds.
- VIP must not change XP or rankings.
- VIP is delivered only after `successful_payment`.
- Store `telegram_payment_charge_id` for every successful charge.
- Do not store Telegram message text, captions or files.
- AI insights are excluded.

---

### Task 1: Product catalog and billing schema

**Files:**
- Create: `app/services/vip_plans.py`
- Create: `app/billing_models.py`
- Modify: `app/database.py`
- Create: `supabase/migrations/20260723150000_add_vip_stars_billing.sql`
- Test: `tests/test_vip_plans.py`

- [ ] Add failing tests for exact prices, duration, recurring period and public payloads.
- [ ] Implement immutable server-side plan definitions.
- [ ] Add invoice, payment and trial-claim models with unique charge and payload constraints.
- [ ] Import billing models before `Base.metadata.create_all`.
- [ ] Add production migration with indexes, RLS and revoked direct client access.

### Task 2: Atomic billing repository

**Files:**
- Create: `app/repositories/billing.py`
- Test: `tests/test_billing_repository.py`

- [ ] Add failing tests for invoice creation, user/amount validation and trial eligibility.
- [ ] Add failing tests for idempotent charge recording and VIP duration stacking.
- [ ] Add failing tests for recurring Telegram expiry and duplicate-trial refund result.
- [ ] Implement invoice intents and atomic payment processing.
- [ ] Keep `VipGrant` synchronized without granting competitive advantages.

### Task 3: Telegram payment handlers

**Files:**
- Create: `app/bot/routers/payments.py`
- Modify: `app/bot/setup.py`
- Modify: `app/main.py`
- Test: `tests/test_vip_payment_handlers.py`

- [ ] Add failing tests proving invalid checkout is rejected and valid checkout is approved.
- [ ] Add failing tests proving successful payment grants VIP once.
- [ ] Implement `pre_checkout_query` and `successful_payment` handlers.
- [ ] Automatically refund a duplicate trial payment.
- [ ] Register billing repository in both FastAPI state and aiogram dispatcher data.

### Task 4: Billing and export API

**Files:**
- Create: `app/api/billing/__init__.py`
- Create: `app/api/billing/schemas.py`
- Create: `app/api/billing/routes.py`
- Create: `app/services/analytics_exports.py`
- Modify: `app/main.py`
- Modify: `app/api/miniapp/routes.py`
- Test: `tests/test_billing_api.py`

- [ ] Add authenticated plan/status/history endpoints.
- [ ] Add invoice-link endpoint using `XTR` and exact server plan values.
- [ ] Add cancel/resume endpoint for recurring monthly subscription.
- [ ] Add VIP-only CSV and PDF group exports with membership checks.
- [ ] Gate premium report themes for free users while keeping the default theme available.

### Task 5: Featured achievements

**Files:**
- Modify: `app/repositories/achievements.py`
- Create: `app/api/miniapp/featured.py`
- Modify: `app/main.py`
- Test: `tests/test_featured_achievements.py`

- [ ] Add failing tests for listing, setting, reordering and removing up to three earned achievements.
- [ ] Require VIP or owner access for mutations.
- [ ] Verify every selected achievement belongs to the current user.
- [ ] Expose featured achievements for profile rendering.

### Task 6: VIP Mini App

**Files:**
- Create: `miniapp/src/vip/VipApp.tsx`
- Create: `miniapp/src/vip/VipApp.test.tsx`
- Create: `miniapp/src/vip/types.ts`
- Create: `miniapp/src/vip/vipApi.ts`
- Create: `miniapp/src/styles/vip.css`
- Modify: `miniapp/src/telegram/sdk.ts`
- Modify: `miniapp/src/main.tsx`
- Modify: `miniapp/src/features/profile/ProfilePage.tsx`

- [ ] Render current VIP state, trial banner, four plan cards and benefits.
- [ ] Open Telegram invoice links with `WebApp.openInvoice`.
- [ ] Refresh status after paid invoices and show errors without losing the page.
- [ ] Show purchase history and monthly cancellation controls.
- [ ] Add a clear profile action that opens `/miniapp/vip`.

### Task 7: Documentation, versions and verification

**Files:**
- Modify: `README.md`
- Modify: `docs/OWNER_PANEL.md`
- Modify: `pyproject.toml`
- Modify: `miniapp/package.json`
- Modify: `app/main.py`

- [ ] Document plans, trial behavior, payment lifecycle, refunds and deployment migration.
- [ ] Set all service versions to `0.7.0`.
- [ ] Run frontend tests, typecheck and production build.
- [ ] Run Ruff, pytest and compileall.
- [ ] Run production Docker build.
- [ ] Open PR, wait for green checks and squash-merge into `main`.
