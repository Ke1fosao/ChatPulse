# ChatPulse Gamification v3 Design

## Scope

This release adds six connected features: custom weekly-report time, `/compare`, message of the week, achievements and levels, activity streaks, and themed weekly-report image cards.

## Confirmed product decisions

- Achievement notifications use a combined mode: important achievements and level-ups are announced immediately; minor achievements appear in `/profile` and weekly reports.
- XP is weighted: qualifying text message `+1`, reply `+2`, photo or voice/video-note `+2`, received reaction `+3`.
- Anti-spam is strict: five-second XP cooldown, exact and near-duplicate blocking, burst reduction after 20 messages in ten minutes, zero XP at extreme bursts, and daily caps.
- Group cap: 200 XP per user per group per local day.
- Global cap: 400 XP per user across ChatPulse per UTC day.
- Both group level and global level are displayed.
- Message text is never stored. The database stores Telegram message ID, author, reaction count, keyed exact fingerprint, keyed 64-bit similarity fingerprint, and technical counters only.
- A streak day requires at least 10 group XP.
- Up to three missed days per calendar month are automatically protected. Unused protection does not carry forward.
- Weekly cards have three administrator-selectable themes: `dark_pulse`, `telegram_wave`, and `clean_light`.

## Architecture

Gamification is isolated in `app/repositories/gamification.py` and `app/services/gamification.py`. Existing activity counters remain in `ActivityRepository`; routers call the gamification repository after normal activity tracking. This preserves the current analytics behavior while adding XP, achievements, streaks, and comparison queries.

Report rendering is isolated in `app/services/report_cards.py`. Both manual `/weekly` and scheduled weekly reports use the same payload builder and PNG renderer.

## Data model

Existing tables gain XP, level, streak, theme, message fingerprint, and per-message reaction fields. New tables store daily global XP, monthly streak-protection usage, and earned member achievements. No message text, captions, or file contents are persisted.

## Period semantics

`/compare` compares the current rolling seven-day window including today with the immediately preceding seven-day window in the group timezone.

Message of the week is the tracked message created in the current rolling seven-day window with the highest current reaction count. Public groups use `t.me/<username>/<message_id>` links; private supergroups use `t.me/c/<internal_id>/<message_id>` links.

## Custom report time

Administrators use `/setreporttime HH:MM`. The command validates 24-hour time and stores both hour and minute. Cloud Scheduler should call the internal report endpoint every five minutes so delivery is no more than five minutes late.

## Levels

Level `L` starts at cumulative XP `50 × (L - 1) × L`. Tiers are Newcomer, Bronze, Silver, Gold, and Diamond. Level-ups are announced immediately.

## Error handling and privacy

Failed card rendering falls back to a normal text report. Failed Telegram sends do not mark a scheduled report as delivered. Fingerprints are generated using keyed HMAC/Blake2-compatible hashing with the existing webhook secret so stored values are not plain hashes of short messages.

## Testing

Pure XP, level, duplicate-distance, report-time parsing, comparison formatting, link generation, and card rendering receive unit tests. Repository tests cover caps, streak protection, achievements, and top-message selection. Existing analytics tests must continue to pass.