# ChatPulse Analytics V2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn ChatPulse into a useful group analytics bot with time-period reports, reactions, nominations, administrator settings, duplicate-update protection, and scheduled weekly summaries.

**Architecture:** Extend the existing SQLAlchemy domain with persistent group settings, per-message authorship, reaction aggregates, and processed Telegram updates. Keep command handlers small by moving period calculations, report generation, and settings logic into repository/service modules. Weekly delivery is exposed through a protected HTTP endpoint intended for Google Cloud Scheduler.

**Tech Stack:** Python 3.12, aiogram 3, FastAPI, SQLAlchemy async, PostgreSQL/Supabase, pytest, Ruff.

## Global Constraints

- Do not store message text or downloaded media.
- Only group administrators may change group settings or reset/pause analytics.
- Telegram updates must be idempotent by `update_id`.
- Existing `/stats`, `/top`, `/me`, `/start`, and `/help` behavior must remain compatible.
- Production persistence uses the existing Supabase project `cqluwjnyvgqvjdfomcxn`.

---

### Task 1: Extend persistence and migration

**Files:**
- Modify: `app/models.py`
- Modify: `app/domain.py`
- Modify: `app/repositories/activity.py`
- Modify: Supabase migration `add_chatpulse_analytics_v2`
- Test: `tests/test_activity_repository.py`

- [ ] Add report settings, pause flags, reaction counters, photo/voice/night/morning counters, message-author mapping, reaction emoji totals, and processed update IDs.
- [ ] Add period-aware repository queries for today, seven days, calendar month, and all time.
- [ ] Add idempotent update claiming and message/reaction recording.
- [ ] Add indexes for period and leaderboard queries.

### Task 2: Period statistics and richer formatting

**Files:**
- Modify: `app/services/stats.py`
- Modify: `app/bot/routers/groups.py`
- Create: `app/bot/keyboards_stats.py`
- Test: `tests/test_stats_formatting.py`

- [ ] Implement `/today`, `/week`, `/month`, `/all`.
- [ ] Make `/stats` and `/top` show inline period selectors.
- [ ] Include reactions in group, member, and leaderboard output.

### Task 3: Reactions and nominations

**Files:**
- Create: `app/bot/routers/reactions.py`
- Create: `app/services/nominations.py`
- Modify: `app/bot/setup.py`
- Test: `tests/test_reactions.py`
- Test: `tests/test_nominations.py`

- [ ] Store message ID to author ID without storing message text.
- [ ] Process public `message_reaction` updates and apply positive/negative deltas.
- [ ] Produce weekly nominations for messages, replies, reactions, photos, voices, night activity, and morning activity.

### Task 4: Administrator settings

**Files:**
- Create: `app/bot/routers/settings.py`
- Create: `app/bot/keyboards_settings.py`
- Modify: `app/repositories/activity.py`
- Test: `tests/test_settings.py`

- [ ] Implement `/settings` with inline toggles for pause, weekly reports, timezone, report weekday, and report hour.
- [ ] Verify administrator status before every settings change.
- [ ] Add `/resetstats` with explicit confirmation.

### Task 5: Weekly report delivery

**Files:**
- Create: `app/services/weekly_reports.py`
- Modify: `app/main.py`
- Modify: `app/config.py`
- Test: `tests/test_weekly_reports.py`

- [ ] Add protected `POST /internal/weekly-reports` endpoint using `X-ChatPulse-Scheduler-Secret`.
- [ ] Select due groups in their configured timezone and avoid duplicate weekly sends.
- [ ] Send one formatted weekly summary per due group and persist delivery time.

### Task 6: Reliability, documentation, and verification

**Files:**
- Modify: `app/main.py`
- Modify: `README.md`
- Modify: `.env.example`
- Test: `tests/test_webhook_security.py`

- [ ] Claim Telegram `update_id` before dispatch and skip duplicates.
- [ ] Preserve webhook secret validation and structured error logging.
- [ ] Document Supabase, Cloud Run variables, message reactions, and Google Cloud Scheduler setup.
- [ ] Run `pytest`, `ruff check`, `ruff format --check`, and `compileall` before merge.
