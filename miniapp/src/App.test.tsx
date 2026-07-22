import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";

vi.mock("./api/client", () => ({
  api: {
    home: vi.fn().mockResolvedValue({
      user: { telegram_id: 101, first_name: "Dmytro", display_name: "Dmytro" },
      account: {
        plan: "free",
        is_owner: false,
        is_vip: false,
        vip_expires_at: null,
        entitlements: [],
      },
      global_progress: {
        xp_total: 850,
        level: 4,
        tier: "Новачок",
        progress: 250,
        needed: 400,
        rank: 2,
        total_users: 10,
        percentile: 90,
      },
      level_catalog: {
        max_level: 50,
        current_level: 4,
        next_tier: { level: 5, tier: "Бронза", xp_required: 1000 },
        levels: [],
      },
      quick_stats: {
        xp_today: 18,
        current_streak: 6,
        longest_streak: 12,
        protection_left: 3,
        groups_count: 0,
        messages_7d: 0,
      },
      activity_series: [],
      recent_achievements: [],
      groups: [],
    }),
    groups: vi.fn().mockResolvedValue([]),
    achievements: vi.fn().mockResolvedValue([]),
    rankings: vi.fn(),
    group: vi.fn(),
    updateSettings: vi.fn(),
    resetGroup: vi.fn(),
    profileCard: vi.fn(),
  },
}));

describe("App", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders five Ukrainian navigation tabs and changes active page", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByText("Пульс твого XP")).toBeInTheDocument();
    for (const label of ["Головна", "Групи", "Рейтинг", "Досягнення", "Профіль"]) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }

    await user.click(screen.getByRole("button", { name: "Профіль" }));
    expect(await screen.findByText("Твій прогрес")).toBeInTheDocument();
  });
});
