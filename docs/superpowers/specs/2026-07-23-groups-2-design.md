# ChatPulse Groups 2.0 — Design Specification

## Goal

Turn the Mini App group area from a long statistics screen into a fast, mobile-first group center that helps a user answer four questions immediately:

1. Which group needs attention?
2. How active is this group right now?
3. What changed since the previous period?
4. What can I do next?

The redesign must preserve current XP, ranking, streak, achievement, VIP, privacy, and billing rules.

## Scope

Groups 2.0 includes:

- a redesigned groups list;
- group status and favorites;
- a compact group header with quick actions;
- four internal tabs: Overview, Ranking, Analytics, Awards;
- a server-calculated Group Pulse score;
- a “What’s new” insight feed;
- contextual admin actions;
- mobile-first loading, empty, and error states;
- lazy tab loading and client-side tab caching.

It does not include chat moderation, message text storage, new XP formulas, new ranking formulas, referrals, or a separate social feed.

## Current problems

The current groups list already supports search, sorting, and an admin-only filter, but every card exposes several competing values at once. The current group dashboard renders summary cards, personal progress, charts, VIP analytics, heatmap, top message, leaderboard, and nominations in one long vertical page. This makes the most important information hard to find and causes unnecessary loading on mobile.

## Product approach

Use a “group center” model rather than a single analytics page.

- The groups list is for choosing and prioritizing groups.
- Overview explains the current state in plain language.
- Ranking answers who is leading.
- Analytics contains detailed charts and premium analysis.
- Awards contains nominations and group-related achievements.

This keeps core actions one tap away while moving detailed information into the correct context.

## 1. Groups list

### Header summary

The top of the page shows a compact summary:

- total connected groups;
- groups active in the last 24 hours;
- groups where the current user is an administrator;
- groups requiring setup or attention.

This is not a large dashboard. It is a single compact strip that can collapse on small screens.

### Search and filters

The search field remains. Under it, use horizontally scrollable chips:

- All;
- Active;
- Quiet;
- I’m admin;
- Needs setup;
- Favorites.

Sorting options:

- Smart order;
- Most active;
- Recent activity;
- Highest trend;
- Highest XP.

“Smart order” sorts in this sequence:

1. needs setup;
2. favorites;
3. active groups;
4. quiet groups;
5. newest activity inside each group.

### Group status

Each group receives one derived status:

- `needs_setup`: bot inactive, paused, or missing the required operational state;
- `active`: last tracked activity is within 24 hours;
- `quiet`: no tracked activity within 24 hours;
- `inactive`: no tracked activity within 7 days.

The UI uses short Ukrainian labels and distinct but restrained status treatments. Status is calculated on the server so all clients use the same rules.

### Group card

Each card shows only:

- deterministic gradient avatar based on chat ID;
- group title;
- status badge;
- favorite pin;
- current user rank;
- messages for the selected summary period;
- trend versus the previous comparable period;
- one concise admin badge when applicable.

The card does not display XP, rank, streak, messages, and level as equally prominent values. Secondary information moves to the group dashboard.

Long press is not required. Favorite pin is a visible touch target. Opening a card remains the primary action.

### Favorites persistence

Add `user_group_preferences`:

- `telegram_user_id`;
- `telegram_chat_id`;
- `is_favorite`;
- `created_at`;
- `updated_at`.

The table has a composite primary key, foreign keys with cascade deletion, and RLS enabled. The Mini App API only reads and changes preferences for the authenticated Telegram user.

## 2. Group shell and navigation

### Compact header

The group dashboard header contains:

- back button;
- gradient avatar;
- group title;
- current status;
- Open in Telegram action when a valid link is available;
- Share action;
- Settings icon for administrators.

The current large administrator banner is removed. Admin status becomes a compact badge and settings action in the header.

### Internal tabs

A sticky horizontal tab bar appears below the header:

- Overview;
- Ranking;
- Analytics;
- Awards.

The selected period is shared by Overview, Ranking, and Analytics. Period controls remain visible but compact. Switching tabs must not reset the period or scroll the user back to the top unnecessarily.

## 3. Overview tab

Overview is the default tab and contains only decision-useful content.

### Group Pulse hero

Show a score from 0 to 100 with one plain-language state:

- 0–24: Almost silent;
- 25–49: Quiet;
- 50–69: Stable;
- 70–84: Active;
- 85–100: Very active.

The backend calculates the score from four normalized components:

- 40% message activity compared with the previous equivalent period;
- 25% active member ratio;
- 20% engagement ratio from replies and reactions per message;
- 15% group continuity based on consecutive active days.

Each component is clamped to 0–100 before weighting. The API returns both the final score and component values so the UI does not reimplement business logic.

The hero also returns one positive and, when relevant, one negative explanation, for example:

- “Messages grew by 24%.”
- “Fewer members participated than last week.”

No AI call is required. Explanations are deterministic templates based on the strongest drivers.

### Personal result

Replace the large personal progress panel with a compact card showing:

- current rank;
- level and XP progress;
- current streak;
- change in rank when available.

### Top participants

Show the first three leaderboard users as a compact horizontal row. A “View full ranking” action opens the Ranking tab.

### What’s new

A maximum of five server-generated insight items:

- rank improvement;
- achievement earned in this group during the period;
- new activity record day;
- group continuity milestone;
- most active participant change;
- weekly report ready.

The feed stores or exposes no message text. Insights are generated from existing counters, achievements, daily activity, and ranking snapshots.

When no meaningful event exists, show one neutral summary instead of an empty block.

### Highlight and quick actions

Show the existing top-message metadata card when available, without message text.

User actions:

- open Telegram group when linkable;
- share group summary;
- view ranking.

Administrator actions:

- open settings;
- send report now;
- pause or resume analytics with confirmation.

Admin actions are permission-checked on the backend. The UI never relies on a visible button as authorization.

## 4. Ranking tab

The Ranking tab contains:

- metric switch: XP, Messages, Reactions, Replies, Streak;
- shared period switch;
- current user pinned above or below the list when outside the visible top rows;
- VIP and OWNER identity badges without changing rank calculations;
- rank movement indicator when a previous snapshot exists;
- compact leaderboard rows optimized for one-handed mobile use.

Changing a metric only reloads ranking data, not the whole group dashboard.

## 5. Analytics tab

Analytics contains the detailed data removed from Overview:

- six summary metrics;
- activity chart with metric switch;
- heatmap;
- period comparison;
- premium 90/180/365-day analysis;
- exports near the relevant chart;
- contextual VIP locks for unavailable premium ranges.

Free users keep existing free analytics. VIP entitlements and purchase flows remain unchanged.

Charts use responsive widths, no horizontal page overflow, and skeleton placeholders while loading.

## 6. Awards tab

Awards contains:

- current nominations;
- group-scoped achievements earned by the current user;
- progress toward the nearest group-scoped achievements;
- highlighted rare achievement when available.

The tab reuses existing achievement definitions and does not introduce a second achievement system.

## 7. API and data loading

### List endpoint

Extend the groups list payload with:

- `status`;
- `is_favorite`;
- `bot_operational`;
- `messages_today`;
- `trend`;
- `attention_reason` when status is `needs_setup`.

Add an authenticated favorite endpoint:

- `PUT /api/miniapp/v1/groups/{chat_id}/favorite` with `{ is_favorite: boolean }`.

### Split group endpoints

Replace the single heavy dashboard load in the UI with tab-specific contracts:

- `/groups/{chat_id}/overview?period=`;
- `/groups/{chat_id}/ranking?period=&metric=`;
- `/groups/{chat_id}/analytics?period=`;
- `/groups/{chat_id}/awards?period=`.

Existing endpoint behavior may remain temporarily for compatibility, but the new UI must use the split endpoints.

### Admin actions

Add authenticated, administrator-only endpoints:

- send report now;
- pause analytics;
- resume analytics.

Every action writes to the existing audit mechanism when available.

### Client cache

Cache successful tab payloads in memory by `chat_id + tab + period + metric`. Reopening a previously loaded tab renders cached data immediately and refreshes in the background. A failed background refresh keeps the previous payload and shows a non-blocking retry notice.

## 8. Mobile design rules

- Minimum touch target: 44 px.
- No page-level horizontal overflow.
- Filter chips and tabs may scroll horizontally with hidden scrollbars.
- Sticky tab bar respects Telegram and iPhone safe areas.
- Cards use one clear visual hierarchy, not multiple competing gradients.
- Long group names truncate safely.
- Bottom navigation never overlaps tab content.
- Skeletons match final card dimensions to prevent layout jumps.
- All actions remain usable at 320 px width.

## 9. Empty, loading, and error states

### Empty list

Explain how to add ChatPulse to a group and provide the existing add-to-group action when possible.

### Empty tab

Each tab has its own useful empty state. For example, Analytics explains that statistics appear after tracked activity rather than showing a generic error.

### Partial failure

A failure in Ranking or Analytics must not close the group or erase Overview. Each tab handles its own loading and retry state.

### Permission changes

When the user loses admin rights, hide admin actions after refresh and display a short notice if an attempted action returns 403.

## 10. Privacy and security

- Do not store message text or file contents.
- Group Pulse and insights use counters and metadata only.
- Favorite preferences are private to the authenticated user.
- Admin actions require server-side membership and role checks.
- New tables use RLS.
- Telegram links are generated only from validated usernames or existing safe message URLs.

## 11. Testing

### Backend

- Group status boundary tests: 24 hours and 7 days.
- Group Pulse component and final score boundary tests.
- Deterministic insight generation tests.
- Favorite ownership and RLS-related repository tests.
- Admin endpoint authorization tests.
- Split endpoint contract tests.
- No changes to existing XP, streak, ranking, or achievements tests.

### Frontend

- Search, each filter, smart sort, and favorite behavior.
- Group card status and long-title rendering.
- Tab switching and preserved period.
- Cached payload rendering and background refresh failure.
- Overview pulse explanations and empty states.
- Ranking metric changes without full dashboard reload.
- Contextual VIP locks in Analytics.
- Admin actions hidden for non-admin users.
- 320 px mobile layout verification through component-level responsive checks and manual Telegram smoke tests.

### Release gate

The release requires:

- Ruff check and format;
- full pytest suite;
- Python compileall;
- frontend tests;
- TypeScript typecheck;
- Vite production build;
- Docker production build;
- Supabase migration applied and RLS verified;
- manual smoke test in Telegram on iPhone and one Android viewport.

## 12. Delivery plan

Implement as three reviewable pull requests:

1. Backend contracts, preferences, pulse score, insights, and admin actions.
2. Groups list redesign and favorites.
3. Group shell, tabs, Overview, Ranking, Analytics, Awards, and mobile polish.

Each PR must keep `main` deployable and pass the full CI gate before merge.

## Success criteria

Groups 2.0 is successful when:

- a user can identify the most important group from the list in under five seconds;
- Overview communicates group health without reading six raw metrics;
- detailed data is reachable in one tab switch;
- group actions are reachable in one or two taps;
- reopening tabs feels instant after the first load;
- no existing billing, VIP, ranking, streak, or achievement behavior regresses;
- the complete experience works without horizontal overflow at 320 px.