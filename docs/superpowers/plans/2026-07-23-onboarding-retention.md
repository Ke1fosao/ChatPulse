# Onboarding and Retention Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a three-step first-run onboarding flow and low-noise Telegram retention notifications that bring users back without spamming them.

**Architecture:** Onboarding progress is derived from a small persistent group-link record plus existing group activity, then exposed inside the Mini App home payload and rendered as a compact checklist. A separate engagement repository and lifecycle service select due notifications, claim idempotency keys before sending, enforce a daily user cooldown, and reuse the existing scheduler-protected lifecycle endpoint.

**Tech Stack:** Python 3.12, FastAPI, aiogram 3, SQLAlchemy async, PostgreSQL/Supabase, React, TypeScript, Vitest, GitHub Actions.

## Global Constraints

- Keep message contents private; store only IDs, status, timestamps, and aggregate progress.
- Do not send more than one retention notification per user in a 20-hour window.
- Do not change XP, ranking, streak, or achievement formulas.
- Existing users with tracked group activity must appear fully onboarded.
- All notifications must be idempotent.
- Version the release as `0.10.0`.

---

### Task 1: Engagement persistence and onboarding state

**Files:**
- Create: `app/engagement_models.py`
- Create: `app/repositories/engagement.py`
- Modify: `app/database.py`
- Create: `tests/test_engagement_repository.py`
- Create: `supabase/migrations/20260723200000_add_onboarding_retention.sql`

- [ ] Write failing repository tests for onboarding steps, group links, notification claims, and cooldown.
- [ ] Implement models and repository.
- [ ] Add additive migration with RLS enabled.
- [ ] Run focused tests.

### Task 2: Bot onboarding lifecycle

**Files:**
- Create: `app/bot/routers/onboarding.py`
- Modify: `app/bot/setup.py`
- Modify: `app/bot/routers/private.py`
- Modify: `app/bot/routers/groups.py`
- Create: `tests/test_onboarding_router.py`

- [ ] Track `my_chat_member` updates and the user who connected the group.
- [ ] Send concise 1/3 and 2/3 setup messages only on real state changes.
- [ ] Upgrade `/start` to show current progress and the next action.
- [ ] Complete onboarding after the first tracked group message.

### Task 3: Mini App onboarding card

**Files:**
- Modify: `app/api/miniapp/routes.py`
- Modify: `miniapp/src/api/types.ts`
- Create: `miniapp/src/features/onboarding/OnboardingCard.tsx`
- Create: `miniapp/src/styles/onboarding.css`
- Modify: `miniapp/src/features/home/HomePage.tsx`
- Modify: `miniapp/src/main.tsx`
- Create: `miniapp/src/features/onboarding/OnboardingCard.test.tsx`

- [ ] Add onboarding payload with progress, steps, and a Telegram add-to-group URL.
- [ ] Render the card only until all three steps are complete.
- [ ] Add mobile-first styling and accessible CTA buttons.

### Task 4: Retention lifecycle

**Files:**
- Create: `app/services/retention_lifecycle.py`
- Modify: `app/main.py`
- Modify: `app/services/weekly_reports.py`
- Create: `tests/test_retention_lifecycle.py`

- [ ] Send one daily streak-at-risk reminder after 19:00 local time.
- [ ] Send a one-time near-achievement reminder when remaining progress is small.
- [ ] Send a weekly-report-ready private notification to eligible active users.
- [ ] Send a rank-rise notification only when a stored weekly snapshot improves.
- [ ] Reuse the scheduler-protected lifecycle endpoint and return per-type counts.

### Task 5: Release verification

**Files:**
- Modify: `app/main.py`
- Modify: `pyproject.toml`
- Modify: `miniapp/package.json`
- Modify: `tests/test_health.py`

- [ ] Synchronize version `0.10.0`.
- [ ] Run Ruff, full pytest, frontend tests, TypeScript, Vite, compileall, and Docker.
- [ ] Apply the additive Supabase migration and verify RLS.
- [ ] Merge only after the complete CI run is green.
