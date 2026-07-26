# ChatPulse Architecture 2.0 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace overlapping APIs and oversized repositories with typed, transaction-safe modules; protect XP under concurrency; cache Telegram access checks; and make Mini App bootstrap failures independent.

**Architecture:** Keep the stable `/api/miniapp/v1` public prefix and stable repository facade imports. Move behavior behind focused API modules, Pydantic response models, transaction-owning application services, a TTL/LRU Telegram access cache, and resource-specific frontend bootstrap state. PostgreSQL row locks provide cross-instance XP correctness; a keyed async lock provides equivalent deterministic behavior in SQLite tests and same-process requests.

**Tech Stack:** Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 async, PostgreSQL/SQLite, aiogram, React 19, TypeScript, Vitest, Playwright WebKit, GitHub Actions, Docker.

## Global Constraints

- Preserve all existing user-facing behavior except the four explicitly removed legacy endpoints.
- Keep the public API prefix `/api/miniapp/v1`.
- Keep imports `from app.repositories.activity import ActivityRepository` and `from app.repositories.miniapp import MiniAppRepository` valid.
- Positive Telegram access TTL is 60 seconds; negative TTL is 15 seconds; bot-status TTL is 30 seconds; stale grace is 300 seconds.
- Telegram access cache maximum is 10,000 entries and group checks are limited to 8 concurrent Telegram requests.
- Group daily XP cap remains 200; global daily XP cap remains 400.
- API response models use `ConfigDict(extra="forbid")`.
- No new repository implementation file may exceed 350 lines.
- No production behavior change is accepted without a failing regression test first.
- Never log Telegram bot tokens, Mini App init data, or raw webhook payloads.

---

### Task 1: Freeze Legacy API Removal and Typed Contract Boundaries

**Files:**
- Create: `tests/test_miniapp_api_contracts.py`
- Create: `miniapp/src/api/legacy-api.test.ts`
- Modify: `miniapp/src/api/client.ts`
- Later modify: API route modules created in Task 6

**Interfaces:**
- Produces: a test-backed list of removed paths and removed TypeScript methods.
- Removed paths: `/groups`, `/groups/{chat_id}`, `/groups/{chat_id}/rankings`, `/profile-card`.
- Canonical paths remain available through Groups 2.0 and showcase endpoints.

- [ ] **Step 1: Write backend tests for removed and canonical paths**

Create tests that build the FastAPI app with existing test settings and assert:

```python
@pytest.mark.parametrize(
    "path",
    [
        "/api/miniapp/v1/groups",
        "/api/miniapp/v1/groups/-1001",
        "/api/miniapp/v1/groups/-1001/rankings",
        "/api/miniapp/v1/profile-card",
    ],
)
async def test_legacy_miniapp_paths_are_not_registered(client, path):
    response = await client.get(path)
    assert response.status_code == 404
```

Also inspect `app.openapi()` and assert canonical paths are registered.

- [ ] **Step 2: Write frontend source regression test**

Read `client.ts` and assert it does not contain:

```typescript
expect(source).not.toContain("group: (chatId");
expect(source).not.toContain("rankings: (chatId");
expect(source).not.toContain('requestBlob("/profile-card")');
expect(source).not.toContain('request<{ groups:');
```

The test must explicitly allow `/groups-v2`, `/ranking`, and `/profile-card-showcase`.

- [ ] **Step 3: Run tests and verify RED**

Run:

```bash
pytest -q tests/test_miniapp_api_contracts.py
cd miniapp && npm test -- --run src/api/legacy-api.test.ts
```

Expected: backend and frontend tests fail because legacy handlers and methods still exist.

- [ ] **Step 4: Remove only unused frontend methods**

Delete `api.group`, `api.rankings`, and any old profile-card request. Do not remove settings, reset, weekly card, Groups 2.0, or showcase methods.

- [ ] **Step 5: Keep backend tests RED until Task 6**

Run the frontend test and full typecheck. Backend removal remains intentionally failing until route decomposition.

- [ ] **Step 6: Commit**

```bash
git add miniapp/src/api/client.ts miniapp/src/api/legacy-api.test.ts tests/test_miniapp_api_contracts.py
git commit -m "test: freeze canonical Mini App API contract"
```

### Task 2: Add Telegram Access TTL/LRU Cache

**Files:**
- Create: `app/services/telegram_access_cache.py`
- Modify: `app/services/telegram_access.py`
- Create: `tests/test_telegram_access_cache.py`
- Modify: `tests/test_telegram_access.py`

**Interfaces:**
- Produces:

```python
@dataclass(frozen=True, slots=True)
class CachedTelegramStatus:
    status: str | None
    fresh: bool
    stale: bool


class TelegramAccessCache:
    async def get_or_load(
        self,
        key: tuple[str, int, int],
        loader: Callable[[], Awaitable[str | None]],
        *,
        positive_ttl: float,
        negative_ttl: float,
        stale_grace: float,
    ) -> CachedTelegramStatus: ...
    async def invalidate_user(self, chat_id: int, user_id: int) -> None: ...
    async def invalidate_group(self, chat_id: int) -> None: ...
    async def clear(self) -> None: ...
```

- `TelegramAccessService.check_member`, `check_admin`, and `get_bot_status` keep their existing signatures.

- [ ] **Step 1: Write failing cache tests**

Cover:

- positive value reused for 60 seconds;
- negative value expires after 15 seconds;
- bot status expires after 30 seconds;
- stale value used after loader failure within 300 seconds;
- no value + loader failure returns `None`;
- two concurrent misses invoke loader once;
- entry 10,001 evicts the least recently used key;
- invalidation by user and group.

Use a fake monotonic clock injected into the cache.

- [ ] **Step 2: Verify RED**

```bash
pytest -q tests/test_telegram_access_cache.py
```

Expected: import failure because `TelegramAccessCache` does not exist.

- [ ] **Step 3: Implement minimal cache**

Use `OrderedDict`, an `asyncio.Lock` for metadata, and a per-key `asyncio.Task` map for request coalescing. Loader exceptions must not be stored as values.

- [ ] **Step 4: Integrate into TelegramAccessService**

Normalize raw statuses once. Owner admin bypass remains before cache lookup. Add `invalidate_user`, `invalidate_group`, and `clear_cache` forwarding methods.

- [ ] **Step 5: Verify cache and existing access tests GREEN**

```bash
pytest -q tests/test_telegram_access_cache.py tests/test_telegram_access.py
```

- [ ] **Step 6: Commit**

```bash
git add app/services/telegram_access.py app/services/telegram_access_cache.py tests/test_telegram_access.py tests/test_telegram_access_cache.py
git commit -m "feat: cache Telegram membership and admin status"
```

### Task 3: Make Group Access Reconciliation Concurrent and Bounded

**Files:**
- Create: `app/api/miniapp/access.py`
- Modify: `app/api/miniapp/groups_v2.py` or its Task 6 replacement
- Create: `tests/test_group_access_batch.py`

**Interfaces:**
- Produces:

```python
async def resolve_group_access(
    access_service: TelegramAccessService,
    *,
    user_id: int,
    chat_ids: Sequence[int],
    concurrency: int = 8,
) -> dict[int, GroupAccessSnapshot]: ...
```

`GroupAccessSnapshot` contains `is_member`, `is_admin`, and `bot_status`.

- [ ] **Step 1: Write a failing bounded-concurrency test**

Create a fake service that records active calls. Resolve 30 groups and assert:

```python
assert fake.max_active <= 8
assert fake.max_active > 1
assert set(result) == set(chat_ids)
```

Also assert repeated group IDs are requested once.

- [ ] **Step 2: Verify RED**

```bash
pytest -q tests/test_group_access_batch.py
```

- [ ] **Step 3: Implement resolver with `asyncio.Semaphore(8)`**

Use one task per unique chat ID and `asyncio.gather`. Do not make nested duplicate admin/member Telegram calls; derive both from one cached raw status request where possible.

- [ ] **Step 4: Replace sequential group loops**

Use the batch resolver in group list and home group capability enrichment. Bot-status reconciliation writes only changed statuses.

- [ ] **Step 5: Verify GREEN**

```bash
pytest -q tests/test_group_access_batch.py tests/test_groups_v2_api.py
```

- [ ] **Step 6: Commit**

```bash
git add app/api/miniapp/access.py app/api/miniapp/groups_v2.py tests/test_group_access_batch.py
git commit -m "perf: batch Telegram group access checks"
```

### Task 4: Protect XP with Deterministic Locks

**Files:**
- Create: `app/services/keyed_lock.py`
- Modify: `app/repositories/gamification.py`
- Modify: `app/models.py` only when an index/constraint is missing
- Create: `tests/test_xp_concurrency.py`
- Modify: migration only when a new database constraint is required

**Interfaces:**
- Produces:

```python
class KeyedAsyncLock:
    @asynccontextmanager
    async def hold(self, key: Hashable) -> AsyncIterator[None]: ...
```

- `GamificationRepository.award_message_xp` and `award_reaction_xp` signatures stay stable.
- Internal `_lock_xp_rows(...)` returns locked `group`, `user`, `member`, `author`, `daily`, and `global_daily` records.

- [ ] **Step 1: Write concurrent failing tests**

Tests must launch parallel `asyncio.gather` calls and assert:

```python
assert member.xp_total == sum(update.group_xp_awarded for update in updates)
assert member.xp_total <= GROUP_DAILY_XP_CAP
assert user.global_xp_total <= GLOBAL_DAILY_XP_CAP
assert author.xp_awarded <= expected_single_message_award
assert member.level == level_for_xp(member.xp_total)
```

Add a same-message test where 20 parallel awards produce one non-zero update.

- [ ] **Step 2: Verify RED repeatedly**

Run the concurrency file at least five times:

```bash
for i in 1 2 3 4 5; do pytest -q tests/test_xp_concurrency.py || exit 1; done
```

Expected: at least one invariant failure on the current implementation.

- [ ] **Step 3: Add keyed lock for SQLite/same-process safety**

Key message awards by `("message", chat_id, message_id)` and reaction/user caps by `("xp", chat_id, user_id, local_date)`.

- [ ] **Step 4: Add PostgreSQL row locking**

Use ordered `select(...).with_for_update()` queries. Create missing daily rows with dialect-specific `ON CONFLICT DO NOTHING`, then select them with locks.

- [ ] **Step 5: Make message XP idempotent**

Return zero XP immediately when locked `MessageAuthor.xp_awarded > 0`. Set `xp_awarded` before transaction commit.

- [ ] **Step 6: Prevent duplicate achievements and streak advancement**

Rely on existing unique keys plus locked member/daily rows. Handle a conflict only as an already-earned achievement, never by rolling back unrelated XP.

- [ ] **Step 7: Verify GREEN repeatedly**

```bash
for i in 1 2 3 4 5; do pytest -q tests/test_xp_concurrency.py || exit 1; done
pytest -q tests/test_gamification_repository.py
```

- [ ] **Step 8: Commit**

```bash
git add app/services/keyed_lock.py app/repositories/gamification.py app/models.py migrations tests/test_xp_concurrency.py
git commit -m "fix: serialize concurrent XP awards"
```

### Task 5: Add Transaction-Owned Activity and Group Settings Services

**Files:**
- Create: `app/services/activity_writes.py`
- Create: `app/services/group_settings.py`
- Modify: `app/repositories/activity.py` or Task 7 package internals
- Modify: `app/repositories/gamification.py`
- Modify: group/private bot routers that currently call repositories separately
- Modify: Mini App settings/reset endpoints
- Create: `tests/test_atomic_activity_writes.py`
- Create: `tests/test_atomic_group_settings.py`

**Interfaces:**
- Produces:

```python
class ActivityWriteService:
    async def record_message(...) -> ActivityWriteResult: ...
    async def record_reaction(...) -> ReactionWriteResult: ...

class GroupSettingsService:
    async def update_settings(
        self,
        *,
        actor_user_id: int,
        chat_id: int,
        values: Mapping[str, Any],
    ) -> dict[str, Any]: ...
    async def reset_group(self, *, actor_user_id: int, chat_id: int) -> None: ...
```

- [ ] **Step 1: Write rollback tests**

Inject a failure after the first table mutation and assert all involved tables retain their original values.

For settings, fail after updating report theme but before normal group fields. For reset, fail after deleting daily activity but before achievements.

- [ ] **Step 2: Verify RED**

```bash
pytest -q tests/test_atomic_activity_writes.py tests/test_atomic_group_settings.py
```

- [ ] **Step 3: Extract session-owned repository primitives**

Add internal methods that receive `AsyncSession`; public existing methods wrap them with their own transaction for compatibility.

- [ ] **Step 4: Implement services with one `session.begin()`**

The service, not the repository method, owns the transaction for multi-step operations.

- [ ] **Step 5: Wire bot and API handlers to services**

Register services in FastAPI lifespan state and dispatcher construction. Preserve current response messages and return shapes.

- [ ] **Step 6: Verify GREEN and existing router tests**

```bash
pytest -q tests/test_atomic_activity_writes.py tests/test_atomic_group_settings.py tests/test_group_settings.py tests/test_webhook_security.py
```

- [ ] **Step 7: Commit**

```bash
git add app/services/activity_writes.py app/services/group_settings.py app/repositories app/api app/bot tests/test_atomic_activity_writes.py tests/test_atomic_group_settings.py
git commit -m "refactor: make activity and settings operations atomic"
```

### Task 6: Split Mini App Routers and Add Pydantic Responses

**Files:**
- Create: `app/api/miniapp/responses/common.py`
- Create: `app/api/miniapp/responses/home.py`
- Create: `app/api/miniapp/responses/groups.py`
- Create: `app/api/miniapp/responses/achievements.py`
- Create: `app/api/miniapp/responses/__init__.py`
- Create: `app/api/miniapp/home.py`
- Create: `app/api/miniapp/profile.py`
- Create: `app/api/miniapp/achievements.py`
- Create: `app/api/miniapp/groups.py`
- Create: `app/api/miniapp/group_settings.py`
- Delete: `app/api/miniapp/routes.py`
- Delete: `app/api/miniapp/groups_v2.py`
- Modify: `app/main.py`
- Modify: `tests/test_miniapp_api_contracts.py`
- Create: `tests/test_miniapp_response_models.py`

**Interfaces:**
- Every JSON route has a concrete `response_model`.
- Binary card endpoints return `Response` unchanged.
- `app.main.create_app` includes the new focused routers.

- [ ] **Step 1: Write response-model tests**

Assert canonical OpenAPI operations contain a `$ref` response schema and models reject unknown fields.

- [ ] **Step 2: Verify RED**

```bash
pytest -q tests/test_miniapp_response_models.py tests/test_miniapp_api_contracts.py
```

- [ ] **Step 3: Define response models from current payloads**

Use exact current field names and nullable behavior. Validate representative repository payload fixtures before changing routes.

- [ ] **Step 4: Move handlers without behavior changes**

Move one endpoint family at a time, run its tests, then delete the original handler to avoid duplicate route registration.

- [ ] **Step 5: Remove legacy endpoints**

Do not re-register the four paths listed in Task 1.

- [ ] **Step 6: Register focused routers in `app/main.py`**

Keep route inclusion explicit and ordered before Mini App static catch-all routes.

- [ ] **Step 7: Verify GREEN**

```bash
pytest -q tests/test_miniapp_api_contracts.py tests/test_miniapp_response_models.py tests/test_groups_v2_api.py tests/test_miniapp_api.py
```

- [ ] **Step 8: Commit**

```bash
git add app/api/miniapp app/main.py tests
git commit -m "refactor: split and type Mini App API"
```

### Task 7: Decompose Activity and Mini App Repositories

**Files:**
- Create: `app/repositories/activity/__init__.py`
- Create: `app/repositories/activity/repository.py`
- Create: `app/repositories/activity/writes.py`
- Create: `app/repositories/activity/queries.py`
- Create: `app/repositories/activity/settings.py`
- Create: `app/repositories/activity/shared.py`
- Delete: `app/repositories/activity.py`
- Create: `app/repositories/miniapp/__init__.py`
- Create: `app/repositories/miniapp/repository.py`
- Create: `app/repositories/miniapp/home.py`
- Create: `app/repositories/miniapp/groups.py`
- Create: `app/repositories/miniapp/achievements.py`
- Create: `app/repositories/miniapp/analytics.py`
- Create: `app/repositories/miniapp/shared.py`
- Delete: `app/repositories/miniapp.py`
- Delete: `app/repositories/miniapp_v2.py`
- Create: `tests/test_repository_facades.py`
- Create: `tests/test_repository_file_boundaries.py`

**Interfaces:**
- `ActivityRepository` and `MiniAppRepository` remain importable from their old module paths because the paths become packages.
- `AchievementMiniAppRepository` is removed; premium analytics methods live on canonical `MiniAppRepository`.

- [ ] **Step 1: Write facade and line-boundary tests**

Assert existing imports work and implementation files are at most 350 lines.

- [ ] **Step 2: Verify RED**

The line-boundary test must fail on current monolithic files.

- [ ] **Step 3: Split activity repository by responsibility**

Use mixins or delegation behind one facade. Do not duplicate SQL or serialization helpers.

- [ ] **Step 4: Split miniapp repository and integrate analytics**

Move methods from `miniapp_v2.py` into `analytics.py`. Update `app/main.py` to instantiate only `MiniAppRepository`.

- [ ] **Step 5: Run targeted repository suites after each split**

```bash
pytest -q tests/test_activity_repository.py tests/test_miniapp_repository.py tests/test_repository_facades.py tests/test_repository_file_boundaries.py
```

- [ ] **Step 6: Commit**

```bash
git add app/repositories app/main.py tests/test_repository_facades.py tests/test_repository_file_boundaries.py
git commit -m "refactor: decompose core repositories"
```

### Task 8: Implement Independent Frontend Bootstrap Resources

**Files:**
- Create: `miniapp/src/app/bootstrap/types.ts`
- Create: `miniapp/src/app/bootstrap/resource.ts`
- Create: `miniapp/src/app/bootstrap/useBootstrapResources.ts`
- Create: `miniapp/src/app/bootstrap/useBootstrapResources.test.tsx`
- Modify: `miniapp/src/App.tsx`
- Modify: `miniapp/src/app/AppRoutes.tsx`
- Modify: Groups and Achievements screens to accept local loading/error/retry state
- Delete: `miniapp/src/app/hooks/useAppBootstrap.ts`
- Update: existing bootstrap tests

**Interfaces:**

```typescript
type ResourceState<T> =
  | { status: "idle" | "loading"; data: T | null; error: "" }
  | { status: "success"; data: T; error: "" }
  | { status: "error"; data: T | null; error: string };

interface BootstrapResources {
  home: ResourceState<HomePayload>;
  groups: ResourceState<GroupsV2CardData[]>;
  achievements: ResourceState<Achievement[]>;
  onboarding: ResourceState<OnboardingPayload>;
  blockedAccount: { reason: string | null } | null;
  reloadCritical(): Promise<void>;
  retryGroups(): Promise<void>;
  retryAchievements(): Promise<void>;
  retryOnboarding(): Promise<void>;
}
```

- [ ] **Step 1: Write partial-failure tests**

Test home success + groups failure, home success + achievements failure, onboarding failure, and blocked-account priority.

- [ ] **Step 2: Write stale-request tests**

Start two reloads; resolve the older request last and assert it cannot overwrite the newer data. Unmount and assert no state update warning.

- [ ] **Step 3: Verify RED**

```bash
cd miniapp && npm test -- --run src/app/bootstrap/useBootstrapResources.test.tsx
```

- [ ] **Step 4: Implement resource reducer and request generation token**

Use one `AbortController` per generation. Use independent promises and preserve successful unrelated data during one-resource retry.

- [ ] **Step 5: Update App and routes**

Only `home.status === "error"` shows the full-screen error. Groups and Achievements receive local error cards with retry buttons.

- [ ] **Step 6: Verify GREEN**

```bash
cd miniapp
npm test -- --run
npm run typecheck
npm run build
```

- [ ] **Step 7: Commit**

```bash
git add miniapp/src
git commit -m "refactor: isolate Mini App bootstrap resources"
```

### Task 9: Observability, Documentation, Full Verification, and Delivery

**Files:**
- Modify: `README.md`
- Modify: `.env.example` only if cache settings become configurable
- Modify: `.github/workflows/ci.yml` only for new targeted checks
- Update: `VERSION`
- Create or update: release notes section in README

**Interfaces:**
- Version becomes `0.14.0`.
- Production startup and readiness behavior remain unchanged.

- [ ] **Step 1: Add structured logs**

Log cache hit/miss/stale/eviction, rollback, and XP lock wait time without sensitive payloads.

- [ ] **Step 2: Document architecture and operational behavior**

Document canonical endpoints, removed endpoints, cache TTLs, transaction guarantees, XP locking, and partial frontend loading.

- [ ] **Step 3: Run complete backend verification**

```bash
ruff check .
ruff format --check .
pytest -q
python -m compileall app migrations
alembic upgrade head
```

Expected: all commands exit `0`.

- [ ] **Step 4: Run complete frontend verification**

```bash
cd miniapp
npm ci --no-audit --no-fund
npm test -- --run
npm run typecheck
npm run build
npx playwright install --with-deps webkit
npm run test:e2e
```

Expected: all commands exit `0`.

- [ ] **Step 5: Build production image**

```bash
docker build -t chatpulse:0.14.0 .
```

Expected: exit `0`.

- [ ] **Step 6: Review changed files**

Confirm there are no generated `build/`, test reports, caches, tokens, local databases, or temporary workflows in the diff.

- [ ] **Step 7: Update draft PR with exact verification evidence**

List the exact PR head SHA and every successful CI job. Mark ready only after the exact head is green.

- [ ] **Step 8: Merge into `main`**

Use a merge commit. Do not merge when any required job is missing, queued, skipped unexpectedly, or failed.

## Plan Self-Review

- Every design requirement maps to a task.
- Removed endpoints are exact and test-backed.
- Cache TTLs, stale behavior, LRU size, and concurrency limit are exact.
- Transaction services and XP lock order are explicit.
- Repository facade compatibility and file-size boundaries are tested.
- Frontend critical/optional resource behavior is explicit.
- No `TBD`, `TODO`, or deferred implementation remains.
