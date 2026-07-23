# Achievement Showcase V3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deliver a group-aware achievement collection and profile showcase with usable pinning, chain-based browsing, real XP rewards, and rarity-scaled celebrations.

**Architecture:** Keep the existing achievement definitions and featured table, but treat `achievement_code + scope_key` as the concrete unlock identity. Backend payloads expose earned instances; frontend collection helpers aggregate chains while the showcase editor selects ordered concrete instances. Reward XP is applied transactionally when an unlock is persisted.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy async, pytest, React 19, TypeScript 7, Vitest, Lucide React, CSS.

## Global Constraints

- Preserve existing VIP/Owner access rules.
- Keep legacy featured-achievement `{codes: string[]}` requests working.
- Do not add a destructive database migration.
- Never display raw technical icon keys to users.
- No user-facing achievement text below 10 px.
- Maximum featured achievements remains five.
- Secret achievement conditions remain masked until earned.

---

### Task 1: Concrete earned-instance API

**Files:**
- Modify: `miniapp/src/api/types.ts`
- Modify: `app/repositories/miniapp_v2.py`
- Test: `tests/test_miniapp_achievement_instances.py`

**Interfaces:**
- Produces `AchievementEarnedInstance` with `scope_key`, `telegram_chat_id`, `group_title`, `earned_at`, and `progress`.
- Adds `earned_instances: AchievementEarnedInstance[]` and `primary_scope_key: string | null` to each public achievement.

- [ ] Write a failing backend test proving the same group-scoped definition can expose two earned instances from two groups.
- [ ] Run `pytest tests/test_miniapp_achievement_instances.py -q` and verify the missing `earned_instances` assertion fails.
- [ ] Serialize canonical and legacy unlocks into ordered instance arrays while preserving the current aggregated top-level payload.
- [ ] Run the focused test and existing Mini App API tests.
- [ ] Commit with `feat: expose concrete achievement instances`.

### Task 2: Ordered showcase persistence

**Files:**
- Modify: `app/api/miniapp/featured.py`
- Modify: `app/repositories/featured_achievements.py`
- Modify: `miniapp/src/vip/vipApi.ts`
- Test: `tests/test_featured_achievements.py`

**Interfaces:**
- Accepts `items: Array<{code: string; scope_key: string}>`.
- Keeps `codes: string[]` as a legacy fallback.
- Returns full achievement payloads including `slot`, `scope_key`, `group_title`, and `earned_at`.

- [ ] Write failing tests for concrete group selection, preserved order, duplicate normalization, unearned rejection, and legacy request compatibility.
- [ ] Run the focused test and confirm failures are caused by the old code-only request model.
- [ ] Implement request parsing and repository validation against canonical and legacy unlock sources.
- [ ] Update the TypeScript API client to send ordered concrete items.
- [ ] Run backend focused tests and TypeScript typecheck.
- [ ] Commit with `feat: persist group-aware featured achievements`.

### Task 3: Profile showcase and profile PNG

**Files:**
- Create: `miniapp/src/features/profile/ProfileFeaturedAchievements.tsx`
- Create: `miniapp/src/features/profile/ProfileFeaturedAchievements.test.tsx`
- Modify: `miniapp/src/features/profile/ProfilePage.tsx`
- Modify: `app/api/miniapp/routes.py`
- Modify: `app/services/profile_cards.py`
- Test: `tests/test_profile_card.py`

**Interfaces:**
- `ProfileFeaturedAchievements` loads `vipApi.featured()` and renders up to five tiles.
- Profile card payload includes `featured_achievements`.

- [ ] Write failing frontend tests for actual icons, group labels, empty state, and navigation to configuration.
- [ ] Write a failing backend PNG test proving selected achievements affect the rendered bytes/payload path.
- [ ] Implement the read-only profile showcase below `ProfileHero`.
- [ ] Add featured data to the profile-card endpoint and draw a compact five-badge row.
- [ ] Run focused frontend/backend tests.
- [ ] Commit with `feat: show featured achievements on profiles`.

### Task 4: Showcase editor redesign

**Files:**
- Modify: `miniapp/src/features/achievements/FeaturedAchievements.tsx`
- Create: `miniapp/src/features/achievements/FeaturedAchievements.test.tsx`
- Modify: `miniapp/src/features/achievements/AchievementVisual.tsx`
- Modify: `miniapp/src/styles/featured-premium.css`

**Interfaces:**
- Editor selection identity is `${code}::${scope_key}`.
- Search covers title, description, and group title.
- Ordering supports drag/drop plus explicit up/down buttons.

- [ ] Write failing tests proving raw icon keys are absent, more than 24 achievements remain available, earned secrets are selectable, search works, and ordering updates the API payload.
- [ ] Run the focused Vitest file and verify expected failures.
- [ ] Replace inline technical text with `AchievementIcon`, add preview slots, bottom-sheet editor, filters, all earned instances, ordering and removal controls.
- [ ] Increase all editor typography to at least 10 px.
- [ ] Run focused tests, typecheck, and build.
- [ ] Commit with `feat: redesign achievement showcase editor`.

### Task 5: Chain-based collection

**Files:**
- Create: `miniapp/src/features/achievements/achievementCollection.ts`
- Create: `miniapp/src/features/achievements/achievementCollection.test.ts`
- Create: `miniapp/src/features/achievements/AchievementChainCard.tsx`
- Create: `miniapp/src/features/achievements/AchievementChainDialog.tsx`
- Modify: `miniapp/src/features/achievements/AchievementsPage.tsx`
- Modify: `miniapp/src/components/AchievementCard.tsx`
- Modify: `miniapp/src/styles/achievement-collection.css`

**Interfaces:**
- `buildAchievementCollection(achievements)` returns chain and standalone collection items.
- Chain cards expose `completedStages`, `totalStages`, `currentProgress`, and `nextAchievement`.

- [ ] Write failing pure-helper tests for chain grouping, stage completion, next milestone, and standalone preservation.
- [ ] Write failing page tests for the four primary tabs and one-card-per-chain rendering.
- [ ] Implement the pure grouping helper and chain components.
- [ ] Simplify top-level tabs to All/In progress/Earned/Secret and move category/rarity into filters.
- [ ] Raise card typography and icon sizes to the design minimums.
- [ ] Run focused tests, typecheck, and build.
- [ ] Commit with `feat: group achievement collection into chains`.

### Task 6: One-time achievement XP rewards

**Files:**
- Modify: `app/domain.py`
- Modify: `app/repositories/achievements.py`
- Modify: `app/repositories/gamification_v2.py`
- Test: `tests/test_achievement_rewards.py`

**Interfaces:**
- `AchievementEarned` includes `reward_xp` and `scope`.
- Group achievements increment group and global XP once.
- Global achievements increment global XP once.

- [ ] Write failing tests for group reward application, global-only reward application, duplicate-event idempotency, and transaction rollback.
- [ ] Run the focused test and verify reward balances remain unchanged under the current implementation.
- [ ] Apply rewards after successful unlock insertion in the same transaction, update level fields using existing level helpers, and avoid recursive evaluation.
- [ ] Return awarded XP in unlock events.
- [ ] Run focused and full gamification tests.
- [ ] Commit with `feat: award xp for achievement unlocks`.

### Task 7: Rarity-scaled celebrations

**Files:**
- Modify: `miniapp/src/features/achievements/AchievementCelebration.tsx`
- Modify: `miniapp/src/features/achievements/useAchievementCelebrations.ts`
- Modify: `miniapp/src/features/achievements/AchievementCelebration.test.tsx`
- Modify: `miniapp/src/styles/achievement-celebration.css`

**Interfaces:**
- common/uncommon use `toast` mode;
- rare/epic use `modal` mode;
- legendary/secret use `fullscreen` mode.

- [ ] Add failing tests for all three presentation modes, reward copy, and pin action availability.
- [ ] Run the focused Vitest file and confirm the old always-fullscreen behavior fails.
- [ ] Implement mode mapping, responsive containers, suitable haptics, `+N XP`, and optional pin action using the event achievement instance.
- [ ] Run focused tests, typecheck, and build.
- [ ] Commit with `feat: scale achievement celebrations by rarity`.

### Task 8: Regression and release verification

**Files:**
- Modify: `README.md` only if feature documentation is currently enumerated there.
- Modify: `pyproject.toml` and `miniapp/package.json` version from `0.11.0` to `0.12.0`.

- [ ] Run `pytest -q`.
- [ ] Run `ruff check app tests`.
- [ ] Run `npm --prefix miniapp test -- --run`.
- [ ] Run `npm --prefix miniapp run typecheck`.
- [ ] Run `npm --prefix miniapp run build`.
- [ ] Review the final diff for raw icon-key rendering, text below 10 px, stale three-slot limits, and code-only featured selections.
- [ ] Commit with `release: ship ChatPulse 0.12.0 achievements showcase`.
