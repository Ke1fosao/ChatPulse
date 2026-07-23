import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { App } from "./App";
import { api, ApiError } from "./api/client";

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
      onboarding: {
        completed_steps: 3,
        total_steps: 3,
        is_complete: true,
        primary_action: "done",
        add_group_url: null,
        linked_group: null,
        steps: [
          { id: "start", title: "Запусти ChatPulse", description: "Готово", completed: true },
          { id: "group", title: "Додай у групу", description: "Готово", completed: true },
          {
            id: "activity",
            title: "Створи перший пульс",
            description: "Готово",
            completed: true,
          },
        ],
      },
      global_progress: {
        xp_total: 850,
        level: 4,
        tier: "Бронза",
        progress: 250,
        needed: 400,
        rank: 2,
        total_users: 10,
        percentile: 90,
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
    levels: vi.fn().mockResolvedValue({
      current_level: 4,
      xp_total: 850,
      max_level: 50,
      levels: [
        {
          level: 4,
          tier: "Бронза",
          xp_required: 600,
          xp_to_next: 400,
          is_unlocked: true,
          is_current: true,
          rewards: [],
        },
      ],
    }),
    profileCard: vi.fn().mockResolvedValue(new Blob(["png"], { type: "image/png" })),
    groups: vi.fn().mockResolvedValue([]),
    achievements: vi.fn().mockResolvedValue([]),
    group: vi.fn(),
    updateSettings: vi.fn(),
    resetGroup: vi.fn(),
  },
  ApiError: class ApiError extends Error {
    constructor(
      message: string,
      public readonly status: number,
      public readonly code?: string,
      public readonly reason?: string | null,
    ) {
      super(message);
    }
  },
  downloadBlob: vi.fn(),
}));

const mockedApi = vi.mocked(api);

describe("App", () => {
  beforeEach(() => vi.clearAllMocks());

  it("renders four Ukrainian navigation tabs without a global ranking page", async () => {
    const user = userEvent.setup();
    render(<App />);

    expect(await screen.findByText("Пульс твого XP")).toBeInTheDocument();
    for (const label of ["Головна", "Групи", "Досягнення", "Профіль"]) {
      expect(screen.getByRole("button", { name: label })).toBeInTheDocument();
    }
    expect(screen.queryByRole("button", { name: "Рейтинг" })).not.toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: "Профіль" }));
    expect(await screen.findByText("Твій прогрес")).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: /Усі рівні ChatPulse/ }));
    expect(
      await screen.findByRole("dialog", { name: "Усі рівні ChatPulse" }),
    ).toBeInTheDocument();
    expect(screen.getByText("50")).toBeInTheDocument();
  });

  it("renders a final blocked screen without a retry loop", async () => {
    mockedApi.home.mockRejectedValueOnce(
      new ApiError(
        "Доступ до ChatPulse обмежено адміністратором.",
        403,
        "ACCOUNT_BLOCKED",
        "Порушення правил спільноти",
      ),
    );

    render(<App />);

    expect(await screen.findByRole("heading", { name: "Акаунт заблоковано" })).toBeInTheDocument();
    expect(screen.getByText("Порушення правил спільноти")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /Повторити/ })).not.toBeInTheDocument();
  });
});
