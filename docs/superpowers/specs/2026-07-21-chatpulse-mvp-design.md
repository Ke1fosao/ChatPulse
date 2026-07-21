# ChatPulse MVP Design

## Goal

Build the first deployable version of ChatPulse: a Telegram group analytics bot that registers users automatically, connects to group chats, stores activity counters without storing message text, and exposes basic personal and group statistics.

## User flow

1. A user opens the bot in a private chat and sends `/start`.
2. ChatPulse creates or updates the user's profile from Telegram metadata and returns an "Add to group" button.
3. When the bot is added to a group, it stores the group and reports whether administrator access is still required.
4. Once the bot becomes an administrator, activity tracking for that group becomes active.
5. Every eligible non-command message updates the sender's all-time and daily counters.
6. Group members can use `/stats`, `/top`, and `/me` to inspect activity.

## MVP scope

### Included

- Python 3.12 project.
- aiogram 3 for Telegram updates.
- FastAPI webhook endpoint for Google Cloud Run.
- SQLAlchemy async persistence.
- SQLite for local development and tests.
- PostgreSQL-compatible `DATABASE_URL` for production.
- Automatic user registration on `/start` and first group activity.
- Automatic group registration through `my_chat_member` updates.
- Tracking of messages, media messages, and replies.
- `/start`, `/help`, `/stats`, `/top`, and `/me` commands.
- Health endpoint.
- Dockerfile and deployment documentation.
- Unit and integration-style tests for storage and statistics behavior.

### Excluded from this phase

- Reaction statistics.
- Scheduled daily or weekly reports.
- Group settings wizard.
- Multilingual interface.
- Telegram Mini App.
- Payments or premium plans.
- Storage of message text or media files.

## Architecture

- `app/main.py` owns the FastAPI lifecycle and Telegram webhook endpoint.
- `app/config.py` validates environment variables.
- `app/database.py` creates the async SQLAlchemy engine and sessions.
- `app/models.py` defines users, groups, members, and daily activity tables.
- `app/repositories/activity.py` contains persistence operations.
- `app/services/stats.py` formats query results into bot-facing summaries.
- `app/bot/routers/private.py` handles private-chat registration.
- `app/bot/routers/groups.py` handles membership changes, activity tracking, and group commands.
- `app/bot/keyboards.py` builds reusable Telegram keyboards.

## Data model

### users

- `telegram_id`: Telegram user ID, primary key.
- `username`, `first_name`, `last_name`, `language_code`.
- `created_at`, `updated_at`, `last_activity_at`.

### chat_groups

- `telegram_chat_id`: Telegram chat ID, primary key.
- `title`, `username`.
- `bot_status`.
- `is_active`: true only when the bot is an administrator.
- `timezone`: defaults to `Europe/Kyiv`.
- `created_at`, `updated_at`.

### group_members

- Composite key: `telegram_chat_id`, `telegram_user_id`.
- Current display metadata.
- All-time counters: messages, media, replies.
- `first_seen_at`, `last_seen_at`.

### daily_activity

- Composite key: group, user, UTC activity date.
- Daily counters: messages, media, replies.

## Privacy and safety

- ChatPulse never stores message text, captions, photos, voice files, or documents.
- Bot messages and messages from other bots are ignored.
- Telegram commands are excluded from activity counters.
- Secrets are loaded only from environment variables.
- The webhook path contains a secret token and Telegram's secret header is validated.

## Error handling

- Missing required configuration fails application startup with a clear error.
- Database transactions roll back on failure.
- Commands return a friendly message when a group has no activity yet.
- A global Telegram error handler logs unexpected update failures without exposing internals to users.

## Testing

- Repository tests verify idempotent user/group upserts and counter increments.
- Statistics tests verify ranking order and empty states.
- API tests verify health and webhook-secret rejection.
- The full suite runs with `pytest`.
- Ruff checks formatting and lint rules.
