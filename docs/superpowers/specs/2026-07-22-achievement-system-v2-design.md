# ChatPulse Achievement System 2.0 Design

## Goal

Replace the current ten threshold-only achievements with an event-driven achievement platform that supports a large catalog, chains, rarity-specific visuals, secret achievements, durable celebration delivery, and a full-screen Mini App celebration experience.

## Scope of this release

This release delivers the production foundation and the complete permanent catalog:

- about 70 permanent achievements across activity, dialogue, reactions, media, streaks, levels, rankings, and group milestones;
- six rarities: common, uncommon, rare, epic, legendary, secret;
- group and global scopes;
- chain metadata and stages;
- secret achievement masking before unlock;
- durable achievement unlock and celebration-event records;
- Mini App pending-event polling and one-time acknowledgement;
- full-screen celebration overlay with rarity-specific themes, confetti, haptics, queueing, summary overflow, reduced-motion support, and navigation to the collection;
- redesigned achievement collection with rarity/category filters and richer cards;
- migration/backfill compatibility for the existing ten achievement codes.

Season authoring in Owner Panel and a full seasonal battle pass are intentionally excluded from this release. The schema keeps `season_key` and version fields so seasons can be added without redesigning the engine.

## Current constraints

- Existing achievement codes must remain valid and must not be awarded twice.
- The bot must not store Telegram message text, captions, or media files.
- Progress is derived only from stored numeric aggregates and event metadata already allowed by ChatPulse.
- Frontend never awards achievements and never supplies trusted progress.
- Unlock creation and celebration-event creation happen in the same database transaction.
- Group pause stops progress and unlock evaluation for that group.
- Ordinary members and group administrators cannot manually grant achievements.

## Architecture

### Achievement catalog

`app/achievements/catalog.py` owns immutable definitions. Each definition contains:

- `code`, `title`, `description`;
- `category`, `rarity`, `scope`;
- `icon`, `visual_theme`;
- `hidden`;
- `chain_key`, `chain_stage`, `chain_total`;
- `trigger`;
- `metric`, `threshold`;
- `important`, `reward_xp`, `version`, `season_key`.

The first release uses numeric metric conditions because current ChatPulse storage already supports them safely. The event-driven boundary means only definitions subscribed to the incoming trigger are evaluated.

### Engine

`app/achievements/engine.py` exposes a pure evaluator:

```python
evaluate_event(event, snapshot, existing_codes) -> tuple[AchievementUnlock, ...]
```

The engine:

1. selects definitions by trigger;
2. reads the requested metric from a numeric snapshot;
3. skips already unlocked codes;
4. evaluates threshold conditions;
5. returns immutable unlock values.

The repository is responsible for transactions and persistence.

### Persistence

The existing `member_achievements` table remains the source of truth for group-scoped legacy unlocks. It is extended with rarity/version/final-progress metadata.

New tables:

- `achievement_unlocks`: canonical unlock records for both group and global scope;
- `achievement_events`: durable one-time celebration delivery queue;
- `featured_achievements`: up to three profile pins, reserved for the follow-up profile integration;
- `achievement_progress`: reserved for non-aggregate and seasonal progress; permanent aggregate achievements do not duplicate existing counters.

`achievement_unlocks` has a uniqueness constraint on `(telegram_user_id, scope_key, achievement_code)`.

`achievement_events` tracks `created_at`, `delivered_at`, `seen_at`, and `shared_at`. A celebration is returned while `seen_at IS NULL`.

### Event flow

Supported trigger values in this release:

- `message_created`;
- `reply_created`;
- `media_created`;
- `reaction_received`;
- `streak_updated`;
- `level_changed`;
- `ranking_calculated`;
- `weekly_report_created`.

The current message/reaction XP transaction builds a numeric snapshot after counters and XP are updated, calls the engine for only relevant triggers, stores new unlocks, and creates celebration events atomically.

### Mini App API

New endpoints under `/api/miniapp/v1`:

- `GET /achievement-events?limit=10` returns unseen celebration events ordered oldest first;
- `POST /achievement-events/{event_id}/seen` acknowledges one event for the verified Telegram user;
- `POST /achievement-events/{event_id}/shared` records a share action;
- the existing `GET /achievements` returns richer catalog metadata and progress.

The API verifies Telegram Mini App `initData` through the existing dependency and always scopes queries by the verified Telegram ID.

### Celebration UX

The Mini App checks pending events:

- immediately after core data loads;
- when the page becomes visible;
- every 20 seconds while open.

The first three achievements are shown one by one. If more remain, the fourth screen is a compact summary with the count and rarest items.

Each rarity has a distinct theme:

- common: blue pulse and light confetti;
- uncommon: green particles;
- rare: purple wave;
- epic: pink-purple flare;
- legendary: gold rays and stronger burst;
- secret: dark glitch and rainbow edge.

The overlay supports:

- haptic feedback through Telegram SDK;
- native share/navigation hooks;
- `prefers-reduced-motion` fallback;
- safe-area insets and mobile keyboard independence;
- portal rendering above the bottom navigation.

## Catalog design

The permanent catalog contains staged chains for:

- messages;
- replies;
- reactions;
- photos;
- voice messages;
- XP;
- streaks;
- levels;
- ranking placements;
- active-day and multi-group milestones.

Secret achievements are represented in the same catalog but title, description, icon, threshold, and progress are masked before unlock.

## Backfill

The legacy codes remain unchanged. Existing rows are copied into canonical unlocks without creating individual celebration events. A single synthetic collection-update event is created when backfill discovers additional unlocks, preventing a flood of overlays.

## Security and consistency

- unlock insertion uses database uniqueness constraints;
- duplicate concurrent evaluations are ignored safely;
- event acknowledgement checks the verified Telegram user;
- frontend event IDs are opaque integers and cannot unlock anything;
- hidden conditions are masked server-side;
- no message text is introduced into new tables or API payloads.

## Testing

Backend tests cover:

- catalog size, unique codes, chain consistency, and rarity values;
- trigger-specific evaluation;
- no duplicate unlocks;
- secret masking;
- transaction creation of unlock plus event;
- owner/user isolation of pending and seen events;
- legacy code compatibility.

Frontend tests cover:

- rarity-specific overlay classes;
- queue ordering and acknowledgement;
- three-event cap plus overflow summary;
- reduced-motion rendering;
- secret card masking;
- achievement filters.

The full CI must pass Ruff, Ruff format, pytest, compileall, Vitest, TypeScript, Vite production build, and Docker production build.