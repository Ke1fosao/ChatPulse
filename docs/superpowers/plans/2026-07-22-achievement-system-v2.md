# Achievement System 2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship an event-driven achievement engine with a large permanent catalog, durable one-time celebration events, richer Mini App collection data, and full-screen rarity-specific celebrations.

**Architecture:** Keep definitions and pure evaluation outside the existing gamification service. Persist canonical unlocks and delivery events transactionally from the gamification repository. Expose a user-scoped Mini App API and render celebrations through a portal-based queue controller.

**Tech Stack:** Python 3.12, FastAPI, async SQLAlchemy, PostgreSQL/Supabase, React 19, TypeScript, Vitest, CSS animations, Telegram Mini App SDK.

## Global Constraints

- Existing ten achievement codes remain valid.
- No Telegram message text, captions, or media files are stored.
- Frontend cannot award achievements.
- Unlock and celebration event creation are atomic.
- Duplicate unlocks are prevented by a database uniqueness constraint.
- Celebration events are shown once and acknowledged by the verified Telegram user.
- Reduced-motion users receive a non-animated equivalent.

---

### Task 1: Catalog and pure engine

**Files:**
- Create: `app/achievements/__init__.py`
- Create: `app/achievements/catalog.py`
- Create: `app/achievements/engine.py`
- Modify: `app/domain.py`
- Test: `tests/test_achievement_engine_v2.py`

**Interfaces:**
- Produces `AchievementDefinition`, `AchievementEvent`, `AchievementSnapshot`, `AchievementUnlock`.
- Produces `ACHIEVEMENTS`, `ACHIEVEMENT_BY_CODE`, `definitions_for_trigger()`.
- Produces `evaluate_event(event, snapshot, existing_codes)`.

- [ ] Write catalog invariant tests: at least 65 definitions, unique codes, six valid rarities, valid chain stages, and all ten legacy codes present.
- [ ] Run `pytest tests/test_achievement_engine_v2.py -q` and confirm failure.
- [ ] Implement immutable definitions and about 70 permanent achievements.
- [ ] Implement trigger-filtered pure evaluation and secret metadata.
- [ ] Run focused tests and commit.

### Task 2: Persistence models and migration

**Files:**
- Modify: `app/models.py`
- Create: `tests/test_achievement_models_v2.py`
- Apply production migration through Supabase after CI passes.

**Interfaces:**
- Produces `AchievementUnlockRecord`, `AchievementEventRecord`, `AchievementProgress`, `FeaturedAchievement`.
- Extends `MemberAchievement` with optional final progress/version metadata without changing its primary key.

- [ ] Write model metadata and uniqueness tests.
- [ ] Add SQLAlchemy models, indexes, checks, and timestamps.
- [ ] Verify model creation under SQLite tests.
- [ ] Commit.

### Task 3: Transactional repository integration

**Files:**
- Create: `app/repositories/achievements.py`
- Modify: `app/repositories/gamification.py`
- Modify: `app/main.py`
- Test: `tests/test_achievement_repository_v2.py`
- Modify: `tests/test_gamification_repository.py`

**Interfaces:**
- Produces `AchievementRepository.evaluate_and_record(...)`.
- Produces `list_pending_events(user_id, limit)`, `mark_seen(user_id, event_id)`, and `mark_shared(user_id, event_id)`.
- Gamification repository invokes the achievement repository inside the existing SQLAlchemy transaction.

- [ ] Write failing tests for atomic unlock+event creation and duplicate concurrency behavior.
- [ ] Implement numeric snapshot creation from `GroupMember` and `User`.
- [ ] Dispatch message/reply/media/reaction/streak/level triggers only when relevant.
- [ ] Keep legacy `GamificationUpdate.achievements` announcements working.
- [ ] Run repository and existing gamification tests.
- [ ] Commit.

### Task 4: Rich collection and celebration API

**Files:**
- Modify: `app/repositories/miniapp.py`
- Modify: `app/api/miniapp/routes.py`
- Modify: `app/api/miniapp/schemas.py`
- Test: `tests/test_miniapp_achievement_events.py`
- Modify: `tests/test_miniapp_api.py`

**Interfaces:**
- `GET /api/miniapp/v1/achievement-events?limit=10`.
- `POST /api/miniapp/v1/achievement-events/{event_id}/seen`.
- `POST /api/miniapp/v1/achievement-events/{event_id}/shared`.
- Existing achievements response gains `scope`, `icon`, `visual_theme`, `hidden`, `chain`, and rarity metadata.

- [ ] Write failing API isolation and acknowledgement tests.
- [ ] Implement user-scoped endpoints.
- [ ] Mask secret definitions before unlock.
- [ ] Return richer collection data while preserving old fields.
- [ ] Run API tests and commit.

### Task 5: Frontend types and API client

**Files:**
- Modify: `miniapp/src/api/types.ts`
- Modify: `miniapp/src/api/client.ts`
- Test: `miniapp/src/api/client.test.ts`

**Interfaces:**
- Produces `AchievementRarity`, `AchievementEventPayload`, `AchievementChain`.
- Produces `api.achievementEvents()`, `api.markAchievementSeen()`, and `api.markAchievementShared()`.

- [ ] Add failing client tests for paths and response parsing.
- [ ] Add exact types and methods.
- [ ] Run Vitest and commit.

### Task 6: Full-screen celebration queue

**Files:**
- Create: `miniapp/src/features/achievements/AchievementCelebration.tsx`
- Create: `miniapp/src/features/achievements/AchievementCelebration.test.tsx`
- Create: `miniapp/src/features/achievements/useAchievementCelebrations.ts`
- Create: `miniapp/src/styles/achievement-celebration.css`
- Modify: `miniapp/src/main.tsx`
- Modify: `miniapp/src/App.tsx`
- Modify: `miniapp/src/telegram/sdk.ts`

**Interfaces:**
- Hook polls every 20 seconds, refreshes on visibility, and queues unseen events.
- Overlay acknowledges after dismissal and supports share/open collection.
- At most three individual events are presented before an overflow summary.

- [ ] Write failing tests for queue ordering, acknowledgement, overflow summary, rarity class, and reduced motion.
- [ ] Implement portal overlay and CSS particle/confetti system without external animation dependencies.
- [ ] Add Telegram haptic helpers.
- [ ] Wire hook into `App` and hide bottom navigation while overlay is active.
- [ ] Run frontend tests, typecheck, and build.
- [ ] Commit.

### Task 7: Achievement collection redesign

**Files:**
- Modify: `miniapp/src/features/achievements/AchievementsPage.tsx`
- Modify: `miniapp/src/components/AchievementCard.tsx`
- Create: `miniapp/src/features/achievements/AchievementDetailsDialog.tsx`
- Create: `miniapp/src/features/achievements/AchievementsPage.test.tsx`
- Create: `miniapp/src/styles/achievement-collection.css`
- Modify: `miniapp/src/main.tsx`

**Interfaces:**
- Adds rarity, near-complete, secret, and chain filters.
- Secret locked cards expose no condition or numeric progress.
- Detail dialog displays chain stage, group/date, and full progress when allowed.

- [ ] Write failing UI tests for secret masking and filters.
- [ ] Implement richer cards, summary header, filters, and details dialog.
- [ ] Run frontend tests and commit.

### Task 8: Backfill and compatibility

**Files:**
- Create: `app/services/achievement_backfill.py`
- Create: `tests/test_achievement_backfill.py`
- Modify: `app/api/internal.py` or the existing protected internal router.

**Interfaces:**
- Produces an idempotent protected backfill operation.
- Copies legacy unlocks to canonical records.
- Creates at most one collection-update event per user when new historical unlocks are discovered.

- [ ] Write idempotency and no-event-flood tests.
- [ ] Implement batch backfill.
- [ ] Add protected internal endpoint using the existing scheduler secret pattern.
- [ ] Run tests and commit.

### Task 9: Production verification and migration

**Files:**
- Update: `README.md`
- Update: `.env.example` only if new config is introduced.

- [ ] Run `ruff check .`.
- [ ] Run `ruff format --check .`.
- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall app`.
- [ ] Run `cd miniapp && npm test -- --run`.
- [ ] Run `cd miniapp && npm run typecheck`.
- [ ] Run `cd miniapp && npm run build`.
- [ ] Run `docker build -t chatpulse-achievements-v2:test .`.
- [ ] Apply the Supabase migration with RLS and revoke direct anon/authenticated writes.
- [ ] Open a PR, verify green GitHub Actions, and merge only after all checks pass.
