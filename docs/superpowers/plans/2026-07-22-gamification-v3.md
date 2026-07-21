# ChatPulse Gamification v3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add custom report scheduling, week-over-week comparison, message of the week, XP/levels/achievements, protected streaks, and themed weekly PNG cards.

**Architecture:** Keep raw activity tracking in `ActivityRepository`, add a focused `GamificationRepository`, and share report payload/rendering between manual and scheduled reports. Persist only IDs, counters, keyed fingerprints, and derived statistics—never message text.

**Tech Stack:** Python 3.12, aiogram 3, FastAPI, SQLAlchemy async, PostgreSQL/Supabase, Pillow, pytest, Ruff.

## Global Constraints

- Group XP cap is exactly 200 per local day.
- Global XP cap is exactly 400 per UTC day.
- Streak threshold is exactly 10 group XP.
- Each calendar month provides exactly three protected missed days.
- No message text or caption may be stored.
- Report themes are `dark_pulse`, `telegram_wave`, and `clean_light`.

---

### Task 1: Schema and domain types

**Files:**
- Modify: `app/models.py`
- Modify: `app/domain.py`
- Create: Supabase migration `add_gamification_v3`

- [ ] Add group/global XP, levels, streak state, card theme, message fingerprints, per-message reaction totals, daily global XP, monthly protection usage, and achievements.
- [ ] Apply the matching idempotent Supabase migration with indexes and RLS.
- [ ] Run model import and schema tests.

### Task 2: Pure gamification rules

**Files:**
- Create: `app/services/gamification.py`
- Test: `tests/test_gamification.py`

- [ ] Add keyed fingerprinting and 64-bit near-duplicate fingerprints.
- [ ] Add weighted XP, cooldown, burst multipliers, level thresholds, tiers, and achievement definitions.
- [ ] Add report-time parser and profile/announcement formatters.
- [ ] Verify unit tests fail before implementation and pass after implementation.

### Task 3: Gamification persistence

**Files:**
- Create: `app/repositories/gamification.py`
- Modify: `app/repositories/activity.py`
- Test: `tests/test_gamification_repository.py`

- [ ] Expose the activity session factory and store message fingerprints.
- [ ] Track current per-message reaction totals.
- [ ] Award group/global XP under 200/400 caps.
- [ ] Update streaks and consume at most three monthly protection days.
- [ ] Persist achievements once and return only newly earned items.
- [ ] Add rolling-week comparison and top-message queries.

### Task 4: Telegram commands and notifications

**Files:**
- Modify: `app/bot/setup.py`
- Modify: `app/bot/routers/groups.py`
- Modify: `app/bot/routers/reactions.py`
- Modify: `app/bot/routers/settings.py`
- Modify: `app/bot/keyboards_settings.py`

- [ ] Inject `GamificationRepository` and fingerprint secret.
- [ ] Award XP after tracked messages and positive reaction deltas.
- [ ] Add `/compare`, `/profile`, and `/setreporttime HH:MM`.
- [ ] Announce level-ups and important achievements immediately.
- [ ] Add theme selection to `/settings`.

### Task 5: Weekly report payload and PNG cards

**Files:**
- Create: `app/services/report_cards.py`
- Modify: `app/services/nominations.py`
- Modify: `app/services/weekly_reports.py`
- Modify: `app/bot/routers/groups.py`
- Modify: `pyproject.toml`
- Modify: `Dockerfile`
- Test: `tests/test_report_cards.py`

- [ ] Build one shared weekly payload with summary, nominations, comparison, achievements, and top message.
- [ ] Render 1200×1200 PNGs in all three themes with Ukrainian-capable fonts.
- [ ] Send cards from `/weekly` and the scheduler, with a message link button where available.
- [ ] Fall back to text when rendering fails.

### Task 6: Documentation and full verification

**Files:**
- Modify: `README.md`
- Modify: `pyproject.toml`

- [ ] Document new commands, privacy model, XP rules, themes, and the five-minute scheduler cadence.
- [ ] Run `ruff check .`.
- [ ] Run `ruff format --check .`.
- [ ] Run `pytest -q`.
- [ ] Run `python -m compileall app`.
- [ ] Open a PR only after all checks pass, then merge after green GitHub Actions.