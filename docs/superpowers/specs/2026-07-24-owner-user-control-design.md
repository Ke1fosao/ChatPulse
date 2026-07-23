# Owner User Control Design

## Status

Approved feature scope from the owner: implement the complete user-management set in a separate branch and merge it into `main`. A blocked user must lose access to both the Telegram bot and the Mini App.

## Goal

Turn the current Owner Control user list into a complete, server-enforced account administration system with detailed user profiles, roles and permissions, full blocking, VIP and XP controls, notes and tags, advanced filtering and sorting, bulk actions, direct bot messages, confirmations, and complete audit history.

## Approaches considered

### 1. Frontend-only controls

Fastest visually, but unsafe because blocked users and unauthorized staff could bypass the UI and call APIs or use the bot directly. Rejected.

### 2. Add all logic directly to the existing Owner Panel repository

Keeps file count low, but would make `owner_panel.py` responsible for permissions, restrictions, XP, messaging, notes, tags, and bulk operations. Rejected because it would become difficult to test and maintain.

### 3. Server-enforced control services with a thin Owner API

Recommended and selected. Authorization and restrictions are enforced in backend dependencies and bot middleware. Focused repositories/services handle users, staff access, XP, messaging, and bulk actions. The React UI only exposes capabilities returned by the server.

## Roles and permissions

The singleton `BotOwner` remains the only immutable Owner and can never be blocked, demoted, or deleted.

Non-owner staff are stored separately with one of these roles:

| Capability | Owner | Admin | Moderator | Support |
|---|---:|---:|---:|---:|
| View users and details | Yes | Yes | Yes | Yes |
| View audit | Yes | Yes | Limited to own actions | No |
| Grant/revoke VIP | Yes | Yes | No | No |
| Adjust XP | Yes | Yes | No | No |
| Block/unblock users | Yes | Yes | Yes | No |
| Edit notes/tags | Yes | Yes | Yes | Yes |
| Send bot messages | Yes | Yes | Yes | Yes |
| Run bulk VIP actions | Yes | Yes | No | No |
| Run bulk block actions | Yes | Yes | No | No |
| Run bulk tag/message actions | Yes | Yes | Yes | No |
| Assign staff roles | Yes | No | No | No |

The server returns the actor role and exact permission strings in `/api/owner/v1/session`. Every mutation checks the required permission server-side. The UI hides unavailable actions but is not the security boundary.

## Full account blocking

A user restriction record stores whether the account is blocked, the reason, the actor, and timestamps.

Blocking behavior:

- Mini App authorization returns HTTP `403` with code `ACCOUNT_BLOCKED` before any protected data is loaded.
- The Mini App displays a dedicated blocked screen with the reason when available.
- Aiogram middleware rejects private commands, callbacks, and messages from blocked users.
- Group activity from blocked users is ignored: no commands, XP, streak updates, achievements, or analytics mutations are processed.
- Group chats receive no public block message. In private chat the bot may return one concise access-denied message.
- Owner accounts cannot be blocked.
- Block and unblock require a reason and explicit confirmation.
- Denied access events are recorded with source (`miniapp`, `bot_private`, `bot_group`) and timestamp. Repeated identical group events are coalesced into a short time window to prevent audit flooding while preserving an attempt count.

## Data model

Add a Supabase migration and matching SQLAlchemy models:

### `admin_staff`

- `telegram_user_id` primary key and foreign key to `users.telegram_id`
- `role`: `admin`, `moderator`, or `support`
- `is_active`
- `granted_by_owner_id`
- `created_at`, `updated_at`

### `user_restrictions`

- `telegram_user_id` primary key
- `is_blocked`
- `reason`
- `blocked_by_actor_id`, `blocked_at`
- `unblocked_by_actor_id`, `unblocked_at`, `unblock_reason`
- `updated_at`

### `user_admin_notes`

- `telegram_user_id` primary key
- `note` text, maximum 4000 characters
- `updated_by_actor_id`, `updated_at`

### `user_admin_tags`

- composite primary key: `telegram_user_id`, normalized `tag`
- `created_by_actor_id`, `created_at`
- tags are lower-case, trimmed, 1–32 characters, maximum 10 tags per user

### `user_xp_adjustments`

- `id`
- `telegram_user_id`
- optional `telegram_chat_id`; null means global XP
- signed `amount`
- `reason`
- `actor_telegram_user_id`
- `created_at`

### `admin_message_deliveries`

- `id`
- `telegram_user_id`
- `actor_telegram_user_id`
- `message_text`
- `status`: `pending`, `sent`, or `failed`
- optional safe error code/message
- `created_at`, `sent_at`

### `blocked_access_events`

- `id`
- `telegram_user_id`
- `source`
- `attempt_count`
- `first_attempt_at`, `last_attempt_at`

Existing `OwnerAuditLog` remains the canonical human-readable action history. Every mutation adds an audit entry in the same database transaction as the state change where possible.

## Detailed user card

Selecting a user opens a full-height mobile drawer instead of only the current VIP modal.

The detail payload includes:

- identity: name, username, Telegram ID, language, registration date, last activity;
- access: free/VIP, source of VIP, start and expiry date;
- status: active, inactive, or blocked, including block reason;
- staff role and permissions when present;
- global XP, global level, joined group count;
- group membership summaries with per-group XP and last seen date;
- payment summary: total successful Stars, payment count, last payment, active subscription;
- notes and tags;
- recent XP adjustments, message deliveries, and relevant audit events.

The drawer contains permission-aware actions for VIP, XP, blocking, role, notes/tags, and messaging. Destructive actions require a confirmation screen showing the target user and exact consequence.

## XP adjustments

Owner and Admin may add or remove XP globally or in one selected group.

Rules:

- amount cannot be zero;
- absolute amount is capped at 100,000 per action;
- resulting XP cannot be negative;
- global or group level is recalculated using the existing ChatPulse level formula;
- manual adjustments do not modify daily activity counters or pretend to be earned XP;
- every adjustment writes a ledger row and audit entry with previous and resulting totals.

## Filters and sorting

The users endpoint supports server-side filtering by:

- VIP: all, active, inactive, expiring within seven days;
- account status: all, active, inactive for 30+ days, blocked;
- staff role;
- payment status: all, has successful payments, never paid;
- registration date range;
- tag.

Sorting options:

- last activity newest/oldest;
- registration newest/oldest;
- XP highest/lowest;
- group count highest/lowest;
- total Stars highest/lowest;
- VIP expiry soonest.

Search remains available for name, username, and Telegram ID. Filters are represented in the URL query and executed in SQL, with pagination preserved.

## Notes and tags

Notes are private to staff and never exposed to ordinary Mini App or bot APIs. Empty note content deletes the note. Tags support quick predefined chips and custom values. Changes are audited with safe metadata; audit stores tag names but does not duplicate the full private note body.

## Direct bot messages

Staff with `users.message` permission may send a plain-text private Telegram message to a registered user.

Rules:

- 1–1000 characters;
- no raw HTML or arbitrary parse mode;
- one recipient message is sent through the existing bot instance;
- bulk messages are limited to 50 selected recipients per request and processed sequentially with per-user results;
- Telegram delivery failures do not roll back other successful sends;
- the user may receive messages even while blocked so support can communicate a reason;
- delivery result and actor are persisted and audited.

## Bulk actions

The list allows selecting up to 100 users. Available actions depend on permission:

- grant VIP with permanent or expiry-date mode;
- revoke VIP;
- block or unblock with reason;
- add or remove a tag;
- send one message to up to 50 selected users.

The backend validates every target, prevents actions against the Owner, applies each target independently, and returns `succeeded` and `failed` arrays. The confirmation screen states the selected count and irreversible effects. A parent audit event records the batch, while individual state-changing operations remain traceable per user.

## API design

Keep `/api/owner/v1` and expand it:

- `GET /session` — actor identity, role, permissions.
- `GET /users` — search, filters, sorting, pagination.
- `GET /users/{id}` — complete detail payload.
- `PATCH /users/{id}/note`.
- `POST /users/{id}/tags`, `DELETE /users/{id}/tags/{tag}`.
- `POST /users/{id}/block`, `POST /users/{id}/unblock`.
- `POST /users/{id}/xp-adjustments`.
- `PUT /users/{id}/role`, `DELETE /users/{id}/role`.
- existing VIP endpoints remain compatible.
- `POST /users/{id}/messages`.
- `POST /users/bulk` for supported bulk actions.
- `GET /users/{id}/audit` for user-scoped history.

Mutations use Pydantic schemas with exact confirmation literals, reason length validation, target limits, and permission dependencies.

## Frontend structure

Keep the existing Owner Control visual language and mobile-first layout.

Split the current large `OwnerUsers.tsx` responsibilities into focused components:

- `OwnerUsers.tsx` — list state, filters, selection, pagination;
- `OwnerUserCard.tsx` — compact row/card;
- `OwnerUserDrawer.tsx` — detail loading and tabs;
- `OwnerUserActions.tsx` — permission-aware action launcher;
- `OwnerUserActionModal.tsx` — validated confirmations/forms;
- `OwnerBulkBar.tsx` and `OwnerBulkModal.tsx` — selection and batch actions;
- `ownerUserApi.ts` and expanded types.

The drawer uses tabs: `Огляд`, `Групи`, `Платежі`, `Історія`. Notes and tags remain visible in Overview. Loading, empty, partial failure, and retry states are explicit.

## Error handling and safety

- `401`: invalid Telegram Mini App session.
- `403 PERMISSION_DENIED`: actor lacks the required capability.
- `403 ACCOUNT_BLOCKED`: target user is blocked from normal product access.
- `404`: user does not exist or is not visible to the actor.
- `409`: conflicting state, such as granting an already active role or blocking the Owner.
- `422`: invalid confirmation, reason, amount, target list, or filter.
- Telegram delivery errors are converted to safe user-facing Ukrainian messages and persisted without tokens or request bodies.
- Owner and staff authorization is never inferred from frontend state.
- No secrets, message history, or ordinary user message text are stored.

## Testing

Backend tests cover:

- role permission matrix and immutable Owner;
- Mini App denial for blocked users;
- bot middleware denial in private and group contexts;
- no XP/activity mutations for blocked users;
- block/unblock transaction and audit;
- user detail, payment summary, filters, sorting, and pagination;
- XP non-negative invariant and level recalculation;
- note/tag validation;
- direct and bulk message success/partial failure;
- bulk target limits and per-target authorization;
- migration/model constraints.

Frontend tests cover:

- detail drawer loading and all tabs;
- permission-based action visibility;
- filter/sort query construction;
- selection and bulk limits;
- confirmation validation;
- blocked badge and status;
- action success, partial failure, and retry states;
- responsive rendering of drawer and sticky bulk bar.

Required verification before merge:

```bash
cd miniapp
npm test -- --run
npm run typecheck
npm run build

cd ..
ruff check .
ruff format --check .
pytest -q
python -m compileall app
docker build -t chatpulse-owner-user-control .
```

Merge into `main` only when all checks pass and the branch has no unintended changes outside this feature.

## Non-goals

- No deletion of Telegram user records.
- No access to private Telegram message history.
- No arbitrary HTML message composer.
- No custom permission editor in this version; roles use the fixed matrix above.
- No automatic punishment based on activity metrics.
