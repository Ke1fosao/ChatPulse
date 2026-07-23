# Groups 2.0 Backend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add the server contracts and persistence needed by the Groups 2.0 Mini App without changing existing XP, ranking, streak, achievement, VIP, privacy, or billing behavior.

**Architecture:** Keep the current `MiniAppRepository` as the source for existing statistics and compose it from a focused `GroupsV2Repository`. Put deterministic status, pulse, and insight calculations in a pure service module. Add a separate preferences model and migration, then expose tab-specific and admin-only routes through a dedicated router.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async ORM, aiogram, PostgreSQL/Supabase, SQLite tests, pytest, Ruff.

## Global Constraints

- Do not store message text or file contents.
- Preserve current XP, ranking, streak, achievement, VIP, privacy, and billing rules.
- Admin actions require live server-side Telegram admin checks.
- All new tables use RLS.
- Telegram links are generated only from validated usernames or existing safe message URLs.
- Existing `/api/miniapp/v1/groups/{chat_id}` remains compatible during migration.

---

### Task 1: Pure group status and pulse service

**Files:**
- Create: `app/services/groups_v2.py`
- Test: `tests/test_groups_v2_service.py`

**Interfaces:**
- Produces: `derive_group_status(...) -> GroupStatusPayload`, `calculate_group_pulse(...) -> dict[str, object]`, `build_group_insights(...) -> list[dict[str, object]]`.

- [ ] **Step 1: Write failing tests** for exact 24-hour and 7-day status boundaries, pulse component clamping, score labels, deterministic explanations, and maximum five privacy-safe insights.
- [ ] **Step 2: Run** `pytest tests/test_groups_v2_service.py -q` and verify import failures.
- [ ] **Step 3: Implement** typed pure functions with no database or Telegram dependencies.
- [ ] **Step 4: Run** `pytest tests/test_groups_v2_service.py -q` and expect all tests to pass.
- [ ] **Step 5: Commit** with `feat: add group pulse and status service`.

### Task 2: Favorite preferences persistence

**Files:**
- Create: `app/groups_v2_models.py`
- Modify: `app/database.py`
- Create: `supabase/migrations/20260723210000_add_group_preferences.sql`
- Test: `tests/test_groups_v2_repository.py`

**Interfaces:**
- Produces ORM model `UserGroupPreference` with composite primary key `(telegram_user_id, telegram_chat_id)` and boolean `is_favorite`.

- [ ] **Step 1: Write failing repository tests** proving preferences are private per user and upsert correctly.
- [ ] **Step 2: Run** `pytest tests/test_groups_v2_repository.py -q` and verify the model/repository is missing.
- [ ] **Step 3: Add** the ORM model, schema import, additive migration, indexes, foreign keys, and RLS.
- [ ] **Step 4: Run** the repository tests and expect them to pass after Task 3 repository implementation.
- [ ] **Step 5: Commit** with `feat: add group favorite preferences`.

### Task 3: GroupsV2 repository contracts

**Files:**
- Create: `app/repositories/groups_v2.py`
- Test: `tests/test_groups_v2_repository.py`

**Interfaces:**
- Consumes: `MiniAppRepository`, `UserGroupPreference`, and pure functions from `app/services/groups_v2.py`.
- Produces:
  - `list_groups(user_id, now=None) -> list[dict]`
  - `set_favorite(user_id, chat_id, is_favorite, now=None) -> dict`
  - `get_overview(user_id, chat_id, period, now=None) -> dict | None`
  - `get_ranking(user_id, chat_id, metric, period, now=None) -> dict | None`
  - `get_analytics(user_id, chat_id, period, now=None) -> dict | None`
  - `get_awards(user_id, chat_id, period, now=None) -> dict | None`
  - `record_admin_action(actor_user_id, chat_id, action, metadata, now=None) -> None`

- [ ] **Step 1: Extend failing tests** with active/quiet/inactive/needs-setup list enrichment, favorite ownership, messages today, overview pulse, privacy-safe insights, analytics split payload, awards split payload, and missing-membership behavior.
- [ ] **Step 2: Run** the focused repository test file and verify failures.
- [ ] **Step 3: Implement** the repository as a focused composition layer around existing Mini App queries.
- [ ] **Step 4: Run** `pytest tests/test_groups_v2_repository.py tests/test_miniapp_repository.py -q` and expect both suites to pass.
- [ ] **Step 5: Commit** with `feat: add Groups 2.0 repository contracts`.

### Task 4: Reusable single weekly report sender

**Files:**
- Modify: `app/services/weekly_reports.py`
- Test: `tests/test_weekly_reports.py`

**Interfaces:**
- Produces `send_weekly_report(bot, repository, chat_id, now=None, retention_service=None, mark_sent=True) -> bool`.

- [ ] **Step 1: Add a failing test** proving a single requested report sends one photo or fallback text and returns `True`.
- [ ] **Step 2: Run** the focused test and verify the helper is missing.
- [ ] **Step 3: Extract** current per-group send logic into `send_weekly_report`; keep scheduled behavior unchanged.
- [ ] **Step 4: Run** weekly report and retention tests and expect no regression.
- [ ] **Step 5: Commit** with `refactor: reuse weekly report sender`.

### Task 5: Groups 2.0 API router and admin actions

**Files:**
- Create: `app/api/miniapp/groups_v2.py`
- Modify: `app/api/miniapp/routes.py`
- Modify: `app/main.py`
- Test: `tests/test_groups_v2_api.py`
- Modify: `tests/test_health.py`

**Interfaces:**
- Adds:
  - `PUT /api/miniapp/v1/groups/{chat_id}/favorite`
  - `GET /api/miniapp/v1/groups/{chat_id}/overview`
  - `GET /api/miniapp/v1/groups/{chat_id}/ranking`
  - `GET /api/miniapp/v1/groups/{chat_id}/analytics`
  - `GET /api/miniapp/v1/groups/{chat_id}/awards`
  - `POST /api/miniapp/v1/groups/{chat_id}/report-now`
  - `POST /api/miniapp/v1/groups/{chat_id}/analytics/pause`
  - `POST /api/miniapp/v1/groups/{chat_id}/analytics/resume`
- Extends existing `GET /api/miniapp/v1/groups` through `GroupsV2Repository`.

- [ ] **Step 1: Write failing API tests** for authentication, membership, admin authorization, favorite mutation, split payloads, report-now, pause/resume, and 404/403 responses.
- [ ] **Step 2: Run** `pytest tests/test_groups_v2_api.py -q` and verify route failures.
- [ ] **Step 3: Implement** router dependencies, request schemas, live access checks, audit writes, and app-state wiring.
- [ ] **Step 4: Bump** backend and Mini App package versions to `0.11.0` and update the health contract.
- [ ] **Step 5: Run** API, health, weekly report, and existing Mini App tests.
- [ ] **Step 6: Commit** with `feat: expose Groups 2.0 backend API`.

### Task 6: Release verification

**Files:**
- Modify only files required by concrete verification failures.

- [ ] **Step 1: Run** `ruff check .`.
- [ ] **Step 2: Run** `ruff format --check .`.
- [ ] **Step 3: Run** `pytest -q`.
- [ ] **Step 4: Run** `python -m compileall app`.
- [ ] **Step 5: Run frontend** `npm test -- --run`, `npm run typecheck`, and `npm run build` from `miniapp/`.
- [ ] **Step 6: Run** `docker build -t chatpulse-miniapp:test .`.
- [ ] **Step 7: Apply** migration `add_group_preferences` to Supabase and verify RLS on `user_group_preferences`.
- [ ] **Step 8: Open and merge** the PR only after the full CI gate is green.
