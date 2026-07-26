import { expect, test, type Page, type TestInfo } from "@playwright/test";

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
