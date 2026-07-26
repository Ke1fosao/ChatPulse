from pathlib import Path

ROOT = Path.cwd()


def read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, content: str) -> None:
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(content, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    content = read(path)
    if old not in content:
        raise RuntimeError(f"Expected text missing in {path}: {old[:80]!r}")
    write(path, content.replace(old, new, 1))


def append_once(path: str, marker: str, addition: str) -> None:
    content = read(path)
    if marker not in content:
        write(path, content.rstrip() + "\n\n" + addition.strip() + "\n")


global_css_path = "miniapp/src/styles/global.css"
global_css = read(global_css_path)
legacy_start = global_css.find("\n.bottom-nav {")
if legacy_start != -1:
    legacy_end = global_css.find("\n.spin {", legacy_start)
    if legacy_end == -1:
        raise RuntimeError("Could not locate the end of legacy bottom navigation CSS")
    global_css = global_css[:legacy_start] + global_css[legacy_end:]
global_css = global_css.replace("  .bottom-nav__item span { font-size: 6px; }\n", "")
write(global_css_path, global_css)

write(
    "miniapp/src/styles/css-regressions.test.ts",
    '''import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

function readStyle(name: string): string {
  return readFileSync(resolve(process.cwd(), "src/styles", name), "utf8");
}

describe("global CSS isolation", () => {
  it("does not contain obsolete unnamespaced bottom navigation selectors", () => {
    const globalCss = readStyle("global.css");
    expect(globalCss).not.toMatch(/(^|[,{\\s])\\.bottom-nav(?=[\\s:{.#>])/m);
    expect(globalCss).not.toContain(".bottom-nav__item");
    expect(globalCss).not.toContain("grid-template-columns: repeat(5, 1fr)");
  });

  it("defines four equal namespaced navigation columns", () => {
    const navigationCss = readStyle("bottom-nav-stable.css");
    expect(navigationCss).toContain("grid-template-columns: repeat(4, minmax(0, 1fr))");
    expect(navigationCss).toContain("width: calc((100% - 12px) / 4)");
  });
});
''',
)

bottom_test = read("miniapp/src/components/BottomNav.test.tsx")
bottom_test = bottom_test.replace(
    'import "../styles/bottom-nav-v2.css";',
    'import "../styles/bottom-nav-stable.css";',
)
bottom_test = bottom_test.replace('expect(navStyle.display).toBe("flex");', 'expect(navStyle.display).toBe("grid");')
bottom_test = bottom_test.replace(
    'expect(navStyle.gridTemplateColumns).not.toContain("repeat(5");\n    expect(firstItemStyle.width).toBe("25%");\n    expect(firstItemStyle.maxWidth).toBe("25%");',
    'expect(navStyle.gridTemplateColumns).toContain("repeat(4");\n    expect(firstItemStyle.width).toBe("100%");\n    expect(firstItemStyle.maxWidth).toBe("");',
)
write("miniapp/src/components/BottomNav.test.tsx", bottom_test)
old_nav = ROOT / "miniapp/src/styles/bottom-nav-v2.css"
if old_nav.exists():
    old_nav.unlink()

write(
    "miniapp/playwright.config.ts",
    '''import { defineConfig } from "@playwright/test";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: false,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [["line"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: "http://127.0.0.1:4173",
    browserName: "webkit",
    colorScheme: "dark",
    locale: "uk-UA",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "retain-on-failure",
  },
  webServer: {
    command: "npm run preview -- --port 4173",
    url: "http://127.0.0.1:4173/miniapp/",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
});
''',
)

write(
    "miniapp/e2e/mobile-layout.spec.ts",
    '''import { expect, test, type Page, type TestInfo } from "@playwright/test";

const account = { plan: "free", is_owner: false, is_vip: false, vip_expires_at: null, entitlements: [] };
const onboarding = {
  completed_steps: 3,
  total_steps: 3,
  is_complete: true,
  primary_action: "done",
  add_group_url: null,
  linked_group: null,
  steps: [
    { id: "start", title: "Запусти ChatPulse", description: "Готово", completed: true },
    { id: "group", title: "Додай у групу", description: "Готово", completed: true },
    { id: "activity", title: "Створи перший пульс", description: "Готово", completed: true },
  ],
};
const summary = {
  messages_count: 47,
  media_count: 4,
  replies_count: 11,
  reactions_received: 18,
  photo_count: 3,
  voice_count: 1,
  night_messages_count: 2,
  morning_messages_count: 7,
  xp_earned: 72,
  active_members: 6,
};
const group = {
  telegram_chat_id: -1001234567890,
  title: "ChatPulse Test Group",
  username: "chatpulse_test",
  initials: "CT",
  level: 4,
  xp_total: 850,
  current_streak: 6,
  rank: 2,
  period: summary,
  trend: 18,
  is_admin: true,
  last_activity_at: "2026-07-26T10:00:00+00:00",
  status: { id: "active", label: "Активна", tone: "success" },
  is_favorite: true,
  bot_operational: true,
  messages_today: 12,
  messages_7d: 47,
  attention_reason: null,
};
const home = {
  user: {
    telegram_id: 101,
    first_name: "Дмитро",
    last_name: "Ковтунович",
    display_name: "Дмитро",
    username: "Ke1fosao",
    photo_url: null,
  },
  account,
  global_progress: {
    xp_total: 850,
    level: 4,
    tier: "Бронза",
    progress: 250,
    needed: 400,
    rank: 2,
    total_users: 20,
    percentile: 90,
  },
  quick_stats: {
    xp_today: 18,
    current_streak: 6,
    longest_streak: 12,
    protection_left: 3,
    groups_count: 1,
    messages_7d: 47,
  },
  activity_series: [
    { date: "2026-07-20", xp: 4, messages: 5, reactions: 1 },
    { date: "2026-07-21", xp: 9, messages: 8, reactions: 2 },
    { date: "2026-07-22", xp: 15, messages: 12, reactions: 4 },
    { date: "2026-07-23", xp: 11, messages: 7, reactions: 3 },
    { date: "2026-07-24", xp: 18, messages: 15, reactions: 6 },
  ],
  recent_achievements: [],
  groups: [group],
};

async function installTelegramAndApi(page: Page): Promise<void> {
  await page.addInitScript(() => {
    const callbacks = new Set<() => void>();
    window.Telegram = {
      WebApp: {
        initData: "query_id=test&auth_date=1785050000&hash=test",
        colorScheme: "dark",
        themeParams: {},
        ready() {},
        expand() {},
        close() {},
        setHeaderColor() {},
        setBackgroundColor() {},
        BackButton: {
          show() {},
          hide() {},
          onClick(callback: () => void) { callbacks.add(callback); },
          offClick(callback: () => void) { callbacks.delete(callback); },
        },
        HapticFeedback: { impactOccurred() {}, notificationOccurred() {} },
        openTelegramLink() {},
        openInvoice(_url: string, callback: (status: "pending") => void) { callback("pending"); },
      },
    };
  });

  await page.route("**/api/**", async (route) => {
    const path = new URL(route.request().url()).pathname;
    let status = 200;
    let body: unknown = {};
    if (path === "/api/miniapp/v1/home") body = home;
    else if (path === "/api/miniapp/v1/onboarding") body = onboarding;
    else if (path === "/api/miniapp/v1/groups-v2") body = { groups: [group] };
    else if (path === "/api/miniapp/v1/achievements") body = { achievements: [] };
    else if (path === "/api/miniapp/v1/achievement-events") body = { events: [] };
    else if (path === "/api/miniapp/v1/featured-achievements") body = { items: [] };
    else if (path === "/api/miniapp/v1/premium/context") body = { account, trial_available: true, active_subscription: null };
    else if (path === "/api/owner/v1/session") {
      status = 403;
      body = { detail: "Owner Panel доступна лише команді ChatPulse." };
    } else body = { groups: [], achievements: [], events: [], items: [] };
    await route.fulfill({ status, contentType: "application/json", body: JSON.stringify(body) });
  });
}

async function attachScreenshot(page: Page, testInfo: TestInfo, name: string): Promise<void> {
  await testInfo.attach(name, { body: await page.screenshot({ fullPage: true }), contentType: "image/png" });
}

for (const width of [320, 375, 390, 430]) {
  test(`bottom navigation fills ${width}px viewport in four equal slots`, async ({ page }, testInfo) => {
    await page.setViewportSize({ width, height: 844 });
    await installTelegramAndApi(page);
    await page.goto("/miniapp/");
    const navigation = page.locator(".cp-bottom-nav");
    const items = navigation.locator(":scope > .cp-bottom-nav__item");
    await expect(items).toHaveCount(4);
    await expect(page.getByRole("button", { name: "Головна" })).toBeVisible();
    const navBox = await navigation.boundingBox();
    const itemBoxes = await items.evaluateAll((elements) =>
      elements.map((element) => {
        const rect = element.getBoundingClientRect();
        return { left: rect.left, right: rect.right, width: rect.width };
      }),
    );
    expect(navBox).not.toBeNull();
    expect(Math.abs((navBox?.width ?? 0) - width)).toBeLessThanOrEqual(1);
    const expectedWidth = (width - 12) / 4;
    for (const box of itemBoxes) expect(Math.abs(box.width - expectedWidth)).toBeLessThanOrEqual(1.25);
    expect(Math.abs(itemBoxes[0].left - 6)).toBeLessThanOrEqual(1.25);
    expect(Math.abs(itemBoxes[3].right - (width - 6))).toBeLessThanOrEqual(1.25);
    await attachScreenshot(page, testInfo, `home-${width}`);
  });
}

test("key Mini App routes render in WebKit", async ({ page }, testInfo) => {
  await page.setViewportSize({ width: 390, height: 844 });
  await installTelegramAndApi(page);
  await page.goto("/miniapp/groups");
  await expect(page.getByRole("heading", { name: "Групи" })).toBeVisible();
  await attachScreenshot(page, testInfo, "groups");
  await page.goto("/miniapp/profile");
  await expect(page.getByText("Твій прогрес")).toBeVisible();
  await attachScreenshot(page, testInfo, "profile");
  await page.goto("/miniapp/owner");
  await expect(page.getByRole("heading", { name: "Owner Panel закрито" })).toBeVisible();
  await attachScreenshot(page, testInfo, "owner-gate");
});
''',
)

replace_once(
    "app/main.py",
    '            if claim is UpdateClaim.IN_PROGRESS:\n                return {"ok": True, "in_progress": True}\n',
    '            if claim is UpdateClaim.IN_PROGRESS:\n                raise HTTPException(\n                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,\n                    detail="Telegram update is already being processed",\n                    headers={"Retry-After": "5"},\n                )\n',
)

migration = read("migrations/versions/20260726_0002_retry_safe_updates.py")
migration = migration.replace("from alembic import op\nimport sqlalchemy as sa\n", "import sqlalchemy as sa\nfrom alembic import op\n")
write("migrations/versions/20260726_0002_retry_safe_updates.py", migration)

replace_once("tests/test_owner_repository.py", "yield OwnerRepository(database.session_factory)", "yield OwnerRepository(database.session_factory, allowed_owner_id=101)")
owner_tests = read("tests/test_owner_repository.py")
owner_tests = owner_tests.replace("test_veheblya_can_claim_owner_once", "test_configured_telegram_id_can_claim_owner_once")
owner_tests = owner_tests.replace(
    '''async def test_wrong_username_cannot_claim_owner(owner_repository) -> None:
    result = await owner_repository.claim_owner(
        telegram_user_id=101,
        username="someone_else",
    )

    assert result is OwnerClaimResult.USERNAME_MISMATCH
    assert await owner_repository.is_owner(101) is False
''',
    '''async def test_wrong_telegram_id_cannot_claim_owner(owner_repository) -> None:
    result = await owner_repository.claim_owner(
        telegram_user_id=202,
        username="veheblya",
    )

    assert result is OwnerClaimResult.ID_MISMATCH
    assert await owner_repository.is_owner(202) is False
''',
)
write("tests/test_owner_repository.py", owner_tests)

for path in ("tests/test_admin_access.py", "tests/test_user_control_repository.py"):
    write(path, read(path).replace('OwnerRepository(database.session_factory).claim_owner(101, "veheblya")', 'OwnerRepository(database.session_factory, allowed_owner_id=101).claim_owner(101, "veheblya")'))
replace_once("tests/test_owner_panel_repository.py", "OwnerRepository(database.session_factory)", "OwnerRepository(database.session_factory, allowed_owner_id=101)")
replace_once("tests/test_claimadmin_command.py", '(OwnerClaimResult.USERNAME_MISMATCH, "лише акаунту @veheblya")', '(OwnerClaimResult.ID_MISMATCH, "OWNER_TELEGRAM_ID")')

append_once(
    "tests/test_webhook_security.py",
    "test_failed_update_returns_retryable_error_and_second_delivery_succeeds",
    '''def test_failed_update_returns_retryable_error_and_second_delivery_succeeds() -> None:
    from unittest.mock import AsyncMock

    settings = build_settings()
    app = create_app(settings)
    headers = {"X-Telegram-Bot-Api-Secret-Token": settings.webhook_header_secret}
    payload = {"update_id": 77}
    with TestClient(app, raise_server_exceptions=False) as client:
        dispatcher = app.state.dispatcher
        dispatcher.feed_update = AsyncMock(side_effect=[RuntimeError("boom"), None])
        failed = client.post(settings.webhook_path, headers=headers, json=payload)
        retried = client.post(settings.webhook_path, headers=headers, json=payload)
        duplicate = client.post(settings.webhook_path, headers=headers, json=payload)
    assert failed.status_code == 500
    assert retried.status_code == 200
    assert retried.json() == {"ok": True}
    assert duplicate.status_code == 200
    assert duplicate.json() == {"ok": True, "duplicate": True}
    assert dispatcher.feed_update.await_count == 2
''',
)
append_once(
    "tests/test_readiness.py",
    "test_ready_returns_safe_503_when_database_probe_fails",
    '''def test_ready_returns_safe_503_when_database_probe_fails(tmp_path) -> None:
    from unittest.mock import AsyncMock

    app = create_app(_settings(f"sqlite+aiosqlite:///{tmp_path / 'ready-fail.db'}"))
    with TestClient(app, raise_server_exceptions=False) as client:
        app.state.database.ping = AsyncMock(side_effect=RuntimeError("database secret details"))
        response = client.get("/ready")
    assert response.status_code == 503
    assert response.json() == {
        "detail": {
            "status": "not_ready",
            "components": {"application": "ready", "database": "unavailable"},
        }
    }
    assert "secret details" not in response.text
''',
)
append_once(
    "tests/test_migrations.py",
    "test_alembic_upgrades_legacy_processed_updates_table",
    '''def test_alembic_upgrades_legacy_processed_updates_table(tmp_path: Path) -> None:
    database_path = tmp_path / "legacy.db"
    inspection_url = f"sqlite:///{database_path}"
    engine = create_engine(inspection_url)
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "CREATE TABLE processed_updates ("
            "update_id BIGINT PRIMARY KEY, "
            "update_type VARCHAR(64) NOT NULL, "
            "processed_at DATETIME NOT NULL"
            ")"
        )
        connection.exec_driver_sql(
            "INSERT INTO processed_updates (update_id, update_type, processed_at) "
            "VALUES (1, 'message', '2026-07-26 10:00:00')"
        )
    engine.dispose()
    config = Config("alembic.ini")
    config.set_main_option("sqlalchemy.url", f"sqlite+aiosqlite:///{database_path}")
    command.upgrade(config, "head")
    inspector = inspect(create_engine(inspection_url))
    columns = {column["name"] for column in inspector.get_columns("processed_updates")}
    assert {"status", "attempts", "lease_expires_at", "completed_at", "last_error"} <= columns
''',
)

readme = read("README.md")
readme = readme.replace('cp .env.example .env\nuvicorn', 'cp .env.example .env\nalembic upgrade head\nuvicorn')
readme = readme.replace('copy .env.example .env\nuvicorn', 'copy .env.example .env\nalembic upgrade head\nuvicorn')
readme = readme.replace('cd miniapp\nnpm install\nnpm run dev', 'cd miniapp\nnpm ci\nnpm run dev')
readme = readme.replace('DEFAULT_TIMEZONE=Europe/Kyiv\n```', 'DEFAULT_TIMEZONE=Europe/Kyiv\nOWNER_TELEGRAM_ID=123456789\n```')
readme = readme.replace('Секрети, токени й production-паролі не комітьте в GitHub.', 'Секрети, токени й production-паролі не комітьте в GitHub. `OWNER_TELEGRAM_ID` має містити незмінний числовий Telegram ID власника; username не надає прав адміністратора.')
readme = readme.replace('2. Python 3.12 встановлює backend, шрифти DejaVu й копіює frontend у `/app/miniapp_dist`.', '2. Python 3.12 встановлює backend, шрифти DejaVu й копіює frontend у `/app/miniapp_dist`;\n3. контейнер запускається від непривілейованого користувача, виконує `alembic upgrade head` і лише після успішної міграції стартує Uvicorn.')
readme = readme.replace('Після push у `main` production pipeline збирає один образ і розгортає бота, API та Mini App разом.', 'Після push у `main` production pipeline збирає один образ і розгортає бота, API та Mini App разом. Для Cloud Run використовуйте `/health` як liveness endpoint, а `/ready` як readiness endpoint із реальною перевіркою підключення до бази.\n\n## Надійність production\n\n- Telegram update позначається завершеним лише після успішної обробки dispatcher-ом. Помилка повертає HTTP 500 і дозволяє Telegram повторити доставку.\n- Повторно доставлений завершений update не виконується вдруге. Паралельна доставка захищена п’ятихвилинною lease.\n- Схема production-бази змінюється лише через Alembic.\n- Версія релізу зберігається у `VERSION`.\n- Нижня навігація перевіряється у справжньому WebKit на ключових мобільних ширинах.')
readme = readme.replace('cd miniapp\nnpm install\nnpm test', 'cd miniapp\nnpm ci\nnpm test')
readme = readme.replace('npm run build\n\ncd ..', 'npm run build\nnpx playwright install webkit\nnpm run test:e2e\n\ncd ..')
readme = readme.replace('python -m compileall app\n```', 'python -m compileall app migrations\nalembic upgrade head\n```')
readme = readme.replace('GitHub Actions виконує frontend і backend перевірки паралельно.', 'GitHub Actions паралельно виконує unit-тести, TypeScript, production build, WebKit-перевірки, backend lint/tests, міграційні smoke-тести та Docker-збірку.')
write("README.md", readme)

write(".gitignore", '''__pycache__/
*.py[cod]
.pytest_cache/
.ruff_cache/
.venv/
.env
*.db
.coverage
htmlcov/
.DS_Store
*.egg-info/
miniapp/node_modules/
miniapp/dist/
miniapp/coverage/
miniapp/playwright-report/
miniapp/test-results/
''')
write(".dockerignore", '''.git
.github
.venv
.env
__pycache__
.pytest_cache
.ruff_cache
tests
docs
miniapp/node_modules
miniapp/dist
miniapp/coverage
miniapp/playwright-report
miniapp/test-results
*.db
*.pyc
''')

write(".github/workflows/ci.yml", '''name: CI

on:
  push:
  pull_request:

jobs:
  frontend:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: miniapp
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: miniapp/package-lock.json
      - run: npm ci --no-audit --no-fund
      - name: Run frontend tests
        shell: bash
        run: |
          set +e
          npm test -- --run > ../frontend-test.log 2>&1
          status=$?
          tail -n 200 ../frontend-test.log
          exit $status
      - name: Upload frontend test log
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: frontend-test-log
          path: frontend-test.log
      - run: npm run typecheck
      - run: npm run build

  browser:
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: miniapp
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "22"
          cache: npm
          cache-dependency-path: miniapp/package-lock.json
      - run: npm ci --no-audit --no-fund
      - run: npm run build
      - run: npx playwright install --with-deps webkit
      - name: Run WebKit mobile checks
        run: npm run test:e2e
      - name: Upload Playwright diagnostics
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-diagnostics
          path: |
            miniapp/playwright-report
            miniapp/test-results
          if-no-files-found: ignore

  backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
      - run: pip install -q -e ".[dev]" -c requirements.lock
      - name: Run backend lint
        shell: bash
        run: |
          set +e
          ruff check . > backend-lint.log 2>&1
          status=$?
          cat backend-lint.log
          exit $status
      - name: Upload backend lint log
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: backend-lint-log
          path: backend-lint.log
      - run: ruff format --check .
      - name: Run backend tests
        shell: bash
        run: |
          set +e
          pytest -q > backend-test.log 2>&1
          status=$?
          tail -n 300 backend-test.log
          exit $status
      - name: Upload backend test log
        if: failure()
        uses: actions/upload-artifact@v4
        with:
          name: backend-test-log
          path: backend-test.log
      - run: python -m compileall app migrations

  docker:
    runs-on: ubuntu-latest
    needs: [frontend, browser, backend]
    steps:
      - uses: actions/checkout@v4
      - run: docker build -t chatpulse-miniapp:test .
''')

write("Dockerfile", '''FROM node:22-slim AS miniapp-builder

WORKDIR /build/miniapp
COPY miniapp/package.json miniapp/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY miniapp ./
RUN npm run build

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \\
    PYTHONUNBUFFERED=1 \\
    PIP_NO_CACHE_DIR=1 \\
    MINIAPP_DIST_DIR=/app/miniapp_dist

WORKDIR /app

RUN apt-get update \\
    && apt-get install -y --no-install-recommends fonts-dejavu-core \\
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md VERSION alembic.ini requirements.lock ./
COPY migrations ./migrations
COPY app ./app
COPY --from=miniapp-builder /build/miniapp/dist ./miniapp_dist

RUN pip install --upgrade pip \\
    && pip install --constraint requirements.lock . \\
    && useradd --create-home --uid 10001 chatpulse \\
    && chown -R chatpulse:chatpulse /app

USER chatpulse
EXPOSE 8080
CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:create_app --factory --host 0.0.0.0 --port ${PORT:-8080}"]
''')
