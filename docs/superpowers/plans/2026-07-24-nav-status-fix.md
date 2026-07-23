# Navigation and Group Status Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the five-item bottom navigation with a rounded four-item animated navigation and permanently fix false “Потрібне налаштування” group states.

**Architecture:** The frontend removes global ranking state and uses a four-position CSS sliding indicator driven by the active tab index. The backend stops message tracking from downgrading stored bot privileges and reconciles stale stored bot status against Telegram when Groups V2 is requested.

**Tech Stack:** React 19, TypeScript, CSS, Vitest, Python 3.14, FastAPI, aiogram, SQLAlchemy, pytest.

## Global Constraints

- Keep ranking available inside the Groups 2.0 group center.
- Do not add a new animation dependency.
- Preserve Telegram safe-area handling and reduced-motion accessibility.
- Do not trust stored bot status when Telegram can confirm a newer status.
- Keep CI email noise to one final PR verification run where possible.

---

### Task 1: Four-tab animated bottom navigation

**Files:**
- Modify: `miniapp/src/api/types.ts`
- Modify: `miniapp/src/components/BottomNav.tsx`
- Modify: `miniapp/src/App.tsx`
- Modify: `miniapp/src/styles/global.css`
- Test: `miniapp/src/components/BottomNav.test.tsx`
- Test: `miniapp/src/App.test.tsx`

**Interfaces:**
- Produces: `TabId = "home" | "groups" | "achievements" | "profile"`.
- Produces: a `--active-index` CSS custom property from `BottomNav`.

- [ ] Write frontend tests asserting four navigation buttons, no global “Рейтинг” item, and active indicator movement after selecting another tab.
- [ ] Run `cd miniapp && npm test -- --run` and confirm the new tests fail.
- [ ] Remove ranking state, effects, imports, and rendering from `App.tsx`; keep group-center ranking untouched.
- [ ] Render one sliding `.bottom-nav__indicator` behind four buttons and set `--active-index` from the active tab.
- [ ] Replace the full-width rectangle with a floating rounded capsule, safe-area spacing, polished icon/text transitions, and reduced-motion fallback.
- [ ] Run frontend tests, typecheck, and build.

### Task 2: Prevent bot-status downgrade during message tracking

**Files:**
- Modify: `app/repositories/activity.py`
- Modify: `app/bot/routers/groups.py`
- Test: `tests/test_activity_repository.py`

**Interfaces:**
- Produces: `ActivityRepository.upsert_group(..., preserve_privileged_status: bool = False)`.
- Privileged statuses are `administrator` and `creator`.

- [ ] Write a failing repository test showing that a normal message must not replace stored `administrator` with `member`.
- [ ] Run the targeted pytest and confirm failure.
- [ ] Add `preserve_privileged_status`; when enabled, keep a stored privileged status if the incoming status is non-privileged.
- [ ] Call message-driven `upsert_group` with `preserve_privileged_status=True`; membership events continue using authoritative replacement.
- [ ] Run the targeted test and repository test suite.

### Task 3: Reconcile stale group status with Telegram

**Files:**
- Modify: `app/services/telegram_access.py`
- Modify: `app/repositories/groups_v2.py`
- Modify: `app/api/miniapp/groups_v2.py`
- Test: `tests/test_groups_v2_api.py`

**Interfaces:**
- Produces: `TelegramAccessService.get_bot_status(chat_id: int) -> str | None`.
- Produces: `GroupsV2Repository.sync_bot_status(chat_id: int, status: str, *, is_active: bool) -> None`.

- [ ] Write an API test where the database says `member`, Telegram reports `administrator`, and `/groups-v2` returns a non-warning status while persisting the corrected value.
- [ ] Run the targeted pytest and confirm failure.
- [ ] Resolve the bot account ID once through `get_me`, read its current membership through `get_chat_member`, and return normalized status.
- [ ] Reconcile status before serializing Groups V2 cards; on Telegram failure, retain stored state rather than inventing a downgrade.
- [ ] Run targeted and full backend tests.

### Task 4: Release verification

**Files:**
- Modify version files only if the repository release convention requires it.

- [ ] Run `ruff check .` and `ruff format --check .`.
- [ ] Run full `pytest -q` and `python -m compileall app`.
- [ ] Run `cd miniapp && npm test -- --run && npm run typecheck && npm run build`.
- [ ] Run the repository Docker build through GitHub Actions.
- [ ] Open one PR, verify all jobs are green, and squash-merge into `main`.
