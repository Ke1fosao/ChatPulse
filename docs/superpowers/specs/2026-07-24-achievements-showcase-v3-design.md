# Achievement Showcase V3 Design

## Goal

Turn achievements into a clear collectible system with a visible profile showcase, specific group-aware pinning, readable mobile cards, chain-based progression, meaningful rewards, and celebration intensity matched to rarity.

## Current problems

- Featured slots print the technical `icon` key instead of rendering an icon component.
- Users configure featured achievements inside the collection but cannot clearly see them in the profile.
- Featured ordering appears draggable but has no working reorder interaction.
- The picker truncates earned achievements and hides earned secret achievements.
- Group-scoped unlocks are aggregated by code, so the UI cannot explain which group produced the pinned achievement.
- Achievement cards use text below a comfortable mobile reading size.
- Long chains render as many near-identical cards.
- `reward_xp` exists in definitions but is not surfaced as an actual awarded benefit.
- Every unlock uses the same full-screen celebration weight.

## Product decisions

### Profile showcase

The profile displays a dedicated showcase below the profile hero. It contains up to five featured achievements for VIP/Owner accounts, with the first three visually emphasized. Each tile renders the real achievement icon, rarity treatment, title, and source group. Empty slots explain how to configure the showcase and route to the achievements tab.

The profile PNG card receives a compact row of featured achievement badges so sharing a profile also shares the selected collection identity.

### Pinning model

Pinning identifies a concrete earned instance with the pair `achievement_code + scope_key`. The existing `featured_achievements.scope_key` column remains the durable identity, so no destructive migration is required.

The update API accepts ordered selections:

```json
{
  "items": [
    {"code": "messages_1000", "scope_key": "group:-100123"},
    {"code": "global_xp_10000", "scope_key": "global"}
  ]
}
```

Legacy `{ "codes": [...] }` requests remain accepted temporarily and resolve to the newest valid earned instance.

Achievement collection payloads expose `earned_instances`, each containing `scope_key`, `group_title`, `earned_at`, and final progress. The main collection remains aggregated by definition, while the showcase picker lets the user select a concrete group instance.

### Showcase editor

The current inline selector becomes a compact showcase preview plus a dedicated bottom sheet editor. The editor includes:

- all earned achievements without a 24-item cap;
- earned secret achievements;
- search by title, description, and group;
- rarity filter;
- five ordered slots;
- drag-and-drop on supported devices;
- explicit up/down controls for reliable mobile ordering;
- remove action;
- unsaved-change state and save feedback.

### Collection structure

Achievements with the same `chain.key` render as one chain card rather than one card per threshold. A chain card shows completed stages, total stages, current metric, and the next milestone. Opening it displays the full stage path.

Standalone, ranking, and secret achievements remain individual cards. The top-level tabs become:

- Усі
- У процесі
- Отримані
- Секретні

Detailed category and rarity controls live under one filter button.

### Visual hierarchy

Minimum mobile typography:

- titles: 14–16 px;
- supporting copy: 12–13 px;
- metadata: 10–11 px;
- no user-facing text below 10 px.

Cards use a 52–60 px icon container, one rarity badge, a readable progress row, and an optional pin affordance for earned achievements. Technical icon names are never rendered as text.

### Rewards

Achievement definitions keep `reward_xp`. Newly unlocked achievements award this XP once to both the group progression for group-scoped achievements and global progression. Global achievements award global XP only. Reward application occurs in the same database transaction as unlock persistence and does not recursively create additional achievement events in the same operation.

Unlock payloads expose `reward_xp`, and celebrations explicitly show `+N XP` only after it was awarded.

### Celebrations

- common/uncommon: compact top toast;
- rare/epic: centered modal celebration;
- legendary/secret: full-screen celebration with stronger motion and haptics.

Every celebration can continue, share, open the collection, or pin the concrete earned instance when the account supports featured achievements.

### Error handling

- Invalid or no-longer-earned showcase selections return HTTP 422.
- Duplicate selections are normalized by `code + scope_key` while preserving order.
- A deleted/deactivated group keeps the historical title when available; otherwise the UI labels it as a group achievement.
- Failed showcase loading leaves the profile usable and offers retry.
- Failed reward application rolls back the unlock transaction.

## Components and boundaries

### Backend

- `app/repositories/featured_achievements.py`: validate, order, and serialize concrete featured instances.
- `app/api/miniapp/featured.py`: backward-compatible request schema.
- `app/repositories/miniapp_v2.py`: expose earned instances and aggregated chain progress.
- `app/repositories/achievements.py`: persist unlocks and apply one-time XP rewards.
- `app/services/profile_cards.py`: render featured badges on PNG cards.

### Frontend

- `AchievementVisual.tsx`: the only icon and rarity presentation mapper.
- `FeaturedAchievements.tsx`: showcase preview and editor state.
- `ProfileFeaturedAchievements.tsx`: read-only profile showcase.
- `achievementCollection.ts`: pure grouping/filtering helpers.
- `AchievementChainCard.tsx` and `AchievementChainDialog.tsx`: chain presentation.
- `AchievementCelebration.tsx`: rarity-aware presentation modes.

## Testing

Backend tests cover ordered concrete selection, legacy request compatibility, group-instance serialization, rejection of unearned selections, and one-time XP rewards.

Frontend tests cover technical icon names never appearing, all earned items being searchable, ordering controls, concrete group selection, chain grouping, profile showcase rendering, and rarity-based celebration modes.

Build verification uses:

```bash
pytest -q
ruff check app tests
npm --prefix miniapp test -- --run
npm --prefix miniapp run typecheck
npm --prefix miniapp run build
```
