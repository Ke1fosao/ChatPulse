import { act, renderHook, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { useBootstrapResources } from "./useBootstrapResources";

const mocks = vi.hoisted(() => ({
  homeCore: vi.fn(),
  onboarding: vi.fn(),
  groups: vi.fn(),
  achievements: vi.fn(),
  initTelegram: vi.fn(),
  notify: vi.fn(),
}));

vi.mock("../../api/client", () => ({
  api: {
    homeCore: mocks.homeCore,
    onboarding: mocks.onboarding,
    groups: mocks.groups,
    achievements: mocks.achievements,
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
}));

vi.mock("../../telegram/sdk", () => ({
  initTelegram: mocks.initTelegram,
  notify: mocks.notify,
}));

const home = {
  user: { telegram_id: 101, first_name: "Дмитро", display_name: "Дмитро" },
  account: {
    plan: "free",
    is_owner: false,
    is_vip: false,
    vip_expires_at: null,
    entitlements: [],
  },
  global_progress: {
    xp_total: 10,
    level: 1,
    tier: "Новачок",
    progress: 10,
    needed: 100,
    rank: 1,
    total_users: 1,
    percentile: 100,
  },
  quick_stats: {
    xp_today: 10,
    current_streak: 1,
    longest_streak: 1,
    protection_left: 3,
    groups_count: 0,
    messages_7d: 0,
  },
  activity_series: [],
  recent_achievements: [],
  groups: [],
};

const onboarding = {
  completed_steps: 3,
  total_steps: 3,
  is_complete: true,
  primary_action: "done",
  add_group_url: null,
  linked_group: null,
  steps: [],
};

describe("useBootstrapResources", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mocks.homeCore.mockResolvedValue(home);
    mocks.onboarding.mockResolvedValue(onboarding);
    mocks.groups.mockResolvedValue([]);
    mocks.achievements.mockResolvedValue([]);
  });

  it("keeps critical home available when optional resources fail", async () => {
    mocks.groups.mockRejectedValueOnce(new Error("groups unavailable"));
    mocks.onboarding.mockRejectedValueOnce(new Error("onboarding unavailable"));

    const { result } = renderHook(() => useBootstrapResources());
    await waitFor(() => expect(result.current.home.status).toBe("success"));
    await waitFor(() => expect(result.current.groups.status).toBe("error"));

    expect(result.current.home.data?.user.telegram_id).toBe(101);
    expect(result.current.home.data?.onboarding.is_complete).toBe(true);
    expect(result.current.achievements.status).toBe("success");
  });

  it("retries only the failed resource", async () => {
    mocks.groups.mockRejectedValueOnce(new Error("groups unavailable"));
    const { result } = renderHook(() => useBootstrapResources());
    await waitFor(() => expect(result.current.groups.status).toBe("error"));

    await act(async () => {
      await result.current.retryGroups();
    });

    expect(result.current.groups.status).toBe("success");
    expect(mocks.groups).toHaveBeenCalledTimes(2);
    expect(mocks.homeCore).toHaveBeenCalledTimes(1);
    expect(mocks.achievements).toHaveBeenCalledTimes(1);
  });

  it("initializes Telegram once", async () => {
    const { result } = renderHook(() => useBootstrapResources());
    await waitFor(() => expect(result.current.home.status).toBe("success"));
    expect(mocks.initTelegram).toHaveBeenCalledTimes(1);
  });
});
