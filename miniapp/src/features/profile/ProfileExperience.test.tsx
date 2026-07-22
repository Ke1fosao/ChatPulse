import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import type { HomePayload } from "../../api/types";
import { ShareCardDialog } from "../../components/ShareCardDialog";
import { ProfilePage } from "./ProfilePage";

const mocks = vi.hoisted(() => ({
  profileCard: vi.fn(),
  downloadBlob: vi.fn(),
  notify: vi.fn(),
}));

vi.mock("../../api/client", () => ({
  api: { profileCard: mocks.profileCard },
  downloadBlob: mocks.downloadBlob,
}));

vi.mock("../../telegram/sdk", () => ({
  notify: mocks.notify,
  openTelegramLink: vi.fn(),
}));

const data = {
  user: {
    telegram_id: 101,
    first_name: "Дмитро",
    display_name: "Діма",
    username: "veheblya",
  },
  account: {
    plan: "owner",
    is_owner: true,
    is_vip: false,
    vip_expires_at: null,
    entitlements: ["premium.all"],
  },
  global_progress: {
    xp_total: 1000,
    level: 5,
    tier: "Бронза",
    progress: 0,
    needed: 500,
    rank: 2,
    total_users: 10,
    percentile: 80,
  },
  level_catalog: {
    max_level: 50,
    current_level: 5,
    next_tier: { level: 10, tier: "Срібло", xp_required: 4500 },
    levels: Array.from({ length: 50 }, (_, index) => {
      const level = index + 1;
      return {
        level,
        tier: level >= 50 ? "Легенда" : level >= 35 ? "Діамант" : level >= 20 ? "Золото" : level >= 10 ? "Срібло" : level >= 5 ? "Бронза" : "Новачок",
        xp_required: 50 * index * level,
        xp_to_next: level === 50 ? 0 : 100 * level,
        unlocked: level <= 5,
        is_current: level === 5,
        is_milestone: [1, 5, 10, 20, 35, 50].includes(level),
        milestone_label: ({ 1: "Старт", 5: "Бронза", 10: "Срібло", 20: "Золото", 35: "Діамант", 50: "Легенда" } as Record<number, string>)[level] ?? null,
      };
    }),
  },
  quick_stats: {
    xp_today: 0,
    current_streak: 4,
    longest_streak: 12,
    protection_left: 3,
    groups_count: 2,
    messages_7d: 148,
  },
  activity_series: [],
  recent_achievements: [],
  groups: [],
} as HomePayload;

describe("premium profile experience", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.profileCard.mockResolvedValue(new Blob(["png"], { type: "image/png" }));
    Object.defineProperty(URL, "createObjectURL", {
      configurable: true,
      value: vi.fn(() => "blob:chatpulse-card"),
    });
    Object.defineProperty(URL, "revokeObjectURL", {
      configurable: true,
      value: vi.fn(),
    });
  });

  afterEach(() => cleanup());

  it("shows creator status and opens the complete 50-level roadmap", async () => {
    const user = userEvent.setup();
    render(
      <ProfilePage
        data={data}
        onShare={vi.fn()}
        onOpenAchievements={vi.fn()}
        onOpenGroups={vi.fn()}
      />,
    );

    expect(screen.getByText("CREATOR")).toBeInTheDocument();
    expect(screen.getByText("OWNER ACCESS")).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Відкрити каталог рівнів" }));

    expect(screen.getByRole("dialog", { name: "Усі рівні ChatPulse" })).toBeInTheDocument();
    expect(screen.getByText("50 рівнів")).toBeInTheDocument();
    expect(screen.getByText("Легенда")).toBeInTheDocument();
    expect(screen.getByText("4 500 XP")).toBeInTheDocument();
  });

  it("shares the generated PNG file through the native share sheet", async () => {
    const user = userEvent.setup();
    const share = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(navigator, "share", { configurable: true, value: share });
    Object.defineProperty(navigator, "canShare", {
      configurable: true,
      value: vi.fn(() => true),
    });

    render(<ShareCardDialog data={data} open onClose={vi.fn()} />);

    expect(await screen.findByAltText("PNG-картка профілю ChatPulse")).toHaveAttribute(
      "src",
      "blob:chatpulse-card",
    );

    await user.click(screen.getByRole("button", { name: "Поділитися карткою" }));

    await waitFor(() => {
      expect(share).toHaveBeenCalledTimes(1);
      const payload = share.mock.calls[0][0] as ShareData;
      expect(payload.files?.[0]?.name).toBe("chatpulse-dima-level-5.png");
      expect(payload.text).toContain("CREATOR");
    });
  });
});
