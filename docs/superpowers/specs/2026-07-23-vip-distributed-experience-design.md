# ChatPulse VIP 2.0 — Distributed Experience Design

Date: 2026-07-23
Status: Proposed for implementation

## Goal

Move VIP from one overloaded standalone page into the places where premium capabilities are actually used. The separate VIP route remains only for purchasing, subscription management, payment history, and a compact overview of benefits.

The design must improve conversion without changing XP fairness, privacy rules, or Telegram identity security.

## Scope

Included:

- a clear VIP badge or upgrade call-to-action in the user profile;
- premium locks, previews, and upgrade actions inside the relevant product pages;
- a simplified purchase and subscription-management route;
- extended analytics periods and comparison tools;
- premium exports where group analytics are viewed;
- premium report themes and advanced report scheduling inside group settings;
- featured achievements managed on the achievements page;
- premium visual identity in profile and rankings;
- expiry, cancellation, and failed-renewal lifecycle notifications;
- a yearly personal ChatPulse summary;
- additional streak protection as a VIP entitlement without modifying XP or ranking formulas.

Excluded:

- referral program;
- promo codes;
- AI insights;
- paid XP boosts or ranking advantages;
- changes to message-content privacy.

## UX principles

1. Premium functionality is visible in context instead of hidden.
2. Free users see a useful preview, not a dead disabled control.
3. Every lock explains the benefit in one sentence and offers one clear action.
4. Owners always receive premium access but do not see purchase buttons.
5. VIP users see the active state, not a repeated sales pitch.
6. The purchase path remains short and uses Telegram Stars invoices.

## Shared premium components

### `VipBadge`

Small crown badge used in profile headers, ranking rows, and premium section titles.

States:

- `OWNER`: permanent owner badge;
- `VIP`: active premium badge;
- hidden for free users unless the component is used as an upgrade entry point.

### `VipUpgradeCard`

Reusable contextual upgrade card with:

- lock icon;
- short preview of the hidden capability;
- text `Доступно у VIP`;
- primary action `Відкрити VIP`;
- optional trial text `7 днів за 1 ⭐`, shown only when trial is available.

The card navigates to `/miniapp/vip?source=<placement>` so the purchase route can record where the user came from.

### `VipGate`

Reusable component that receives the verified `AccountAccess` payload and an entitlement key. It must never be the only protection. The server endpoint also enforces the same entitlement.

Modes:

- preview card;
- locked control;
- locked tab;
- hidden premium-only result.

## Profile experience

### Free user

The profile plan card becomes a direct upgrade call-to-action:

- crown icon;
- title `Відкрий ChatPulse VIP`;
- subtitle with the 1-Star trial when available;
- button or full-card click opens `/miniapp/vip?source=profile`.

### VIP user

The profile hero displays a visible `VIP` crown badge. The plan card shows:

- current plan;
- expiry date;
- auto-renew status when applicable;
- tap action opens subscription management.

### Owner

The profile hero displays `OWNER`. The card opens Owner Panel and never shows a purchase CTA.

## Home page

The existing home page remains useful for free users.

Add a `Мій рік у ChatPulse` card after the activity graph:

- free: blurred preview, sample statistics, lock, upgrade action;
- VIP/owner: opens a yearly summary page with total XP, messages, groups, best streak, top month, top achievements, and shareable card.

Add a subtle VIP badge next to the user identity when active.

## Group dashboard

### Free access

Keep existing 7-day and 30-day statistics, core graph, heatmap, leaderboard, nominations, and current period comparison.

### VIP analytics block

Add an `Розширена аналітика` section directly after the regular activity graph.

Free preview:

- disabled period chips `90 днів`, `6 місяців`, `12 місяців`;
- blurred example comparison chart;
- lock and upgrade CTA.

VIP/owner access:

- periods: 90 days, 180 days, 365 days;
- compare any two supported periods;
- metric selector for messages, XP, reactions, replies, media, and active members;
- trend summary with absolute and percentage changes;
- export buttons placed in this section, not on the standalone VIP page.

Server requirements:

- new validated period values;
- maximum date ranges enforced server-side;
- membership check retained;
- premium entitlement checked server-side for extended periods, comparison, and exports.

## Group settings

### Premium themes

Keep the current default theme free. Premium themes display in the existing theme selector with crown and lock markers.

Free users can preview a theme thumbnail but cannot save it. Attempting to select it opens the contextual upgrade sheet.

### Advanced reporting

Weekly reports remain free.

VIP/owner receives:

- a second scheduled report per week;
- custom report period;
- automatic CSV or PDF attachment option;
- delivery reminder before the report;
- premium card themes.

All changes require group-admin permission and premium entitlement.

## Achievements page

Move featured-achievement management from the standalone VIP route into the achievements collection.

Add a `Закріплені у профілі` section below the collection hero.

- free: preview three empty slots plus upgrade CTA;
- VIP/owner: up to five earned achievements can be selected and reordered;
- profile and share card display the selected achievements;
- database slot constraint changes from 1–3 to 1–5.

The standalone VIP page no longer loads all achievements.

## Rankings

VIP and OWNER badges are visual only.

- badge appears beside display name;
- ranking value and sorting remain unchanged;
- no bonus XP, multipliers, protected rank, or paid placement.

## Streak protection

Free rules remain unchanged.

VIP receives an increased monthly protection allowance. The exact allowance is stored as an entitlement constant, initially five protection days per month instead of three.

This affects streak continuity only. It does not award XP or alter leaderboard values.

## Simplified `/miniapp/vip` route

The route contains only:

1. active plan or trial hero;
2. plan cards;
3. Free vs VIP comparison;
4. subscription cancellation or restoration;
5. payment history;
6. purchase success state.

Remove from this route:

- group export controls;
- achievement selection;
- other capability-specific controls.

### Purchase confirmation

Before opening Telegram invoice, show a bottom sheet with:

- plan title;
- price in Stars;
- duration;
- recurring or one-time status;
- renewal explanation;
- confirm button.

### Success state

After a confirmed payment:

- crown animation and light confetti;
- Telegram success haptic;
- exact expiry date;
- button `Переглянути VIP-можливості` returning to the originating placement when available.

## Lifecycle notifications

Send idempotent Telegram notifications:

- immediately after first successful purchase;
- three days before expiry;
- on expiry;
- after auto-renew cancellation;
- after auto-renew restoration;
- when a recurring payment does not extend the subscription by the expected time;
- after a refund.

The existing `vip_notifications` table remains the idempotency ledger.

## Analytics events

Store privacy-safe product events without message content:

- `vip_viewed` with placement source;
- `vip_plan_selected`;
- `vip_invoice_opened`;
- `vip_payment_completed`;
- `vip_payment_canceled`;
- `vip_feature_previewed`;
- `vip_feature_unlocked`.

Fields:

- Telegram user ID;
- event name;
- placement key;
- plan code when relevant;
- timestamp;
- optional JSON metadata limited to enumerated product fields.

These events support conversion analytics in Owner Panel and must have RLS enabled.

## Security and entitlement rules

- Mini App identity continues to use verified Telegram initData.
- All premium checks are server-side in addition to UI locks.
- Owner access bypasses purchase checks but not group membership/privacy checks.
- Export endpoints return 404 for inaccessible groups and 403 for missing premium entitlement.
- Payment prices remain server-defined.
- No message text, caption, file, or private chat content is stored.

## Testing

Backend:

- entitlement checks for every premium endpoint;
- free, VIP, expired VIP, and owner states;
- extended period validation;
- five-slot featured achievements;
- notification idempotency;
- analytics event validation;
- no XP/ranking changes from VIP.

Frontend:

- contextual lock rendering on each target page;
- correct profile states;
- purchase confirmation and success flow;
- navigation source restoration;
- owner sees premium capability without purchase CTA;
- free users cannot invoke premium mutations through disabled UI.

## Rollout

Implement as a dedicated PR before Owner Revenue UI. The backend event schema required by Owner Revenue ships in this PR so the revenue dashboard has conversion data from launch.