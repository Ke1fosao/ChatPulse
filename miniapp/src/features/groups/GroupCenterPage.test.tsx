import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { api } from "../../api/client";
import type { GroupOverviewPayload } from "../../api/groups-v2";
import type { GroupCardData } from "../../api/types";
import { usePremium } from "../../premium/PremiumContext";
import { GroupCenterPage } from "./GroupCenterPage";

vi.mock("../../api/client", () => ({
  api: {
    groupOverview: vi.fn(),
    groupRanking: vi.fn(),
    groupAnalytics: vi.fn(),
    groupAwards: vi.fn(),
    weeklyCard: vi.fn(),
    updateSettings: vi.fn(),
    resetGroup: vi.fn(),
    sendGroupReport: vi.fn(),
    pauseGroupAnalytics: vi.fn(),
    resumeGroupAnalytics: vi.fn(),
  },
  downloadBlob: vi.fn(),
}));

vi.mock("../../premium/PremiumContext", () => ({
  usePremium: vi.fn(),
}));

const group: GroupCardData = {
  telegram_chat_id: -1001,
  title: "ChatPulse Team",
  username: "chatpulse_team",
  initials: "CT",
  level: 4,
  xp_total: 800,
  current_streak: 6,
  rank: 2,
  period: {
    messages_count: 100,
    media_count: 5,
    replies_count: 20,
    reactions_received: 30,
    photo_count: 3,
    voice_count: 2,
    night_messages_count: 2,
    morning_messages_count: 6,
    xp_earned: 300,
    active_members: 8,
  },
  trend: 18,
  is_admin: true,
  last_activity_at: "2026-07-23T12:00:00+00:00",
};

const overview: GroupOverviewPayload = {
  group: {
    telegram_chat_id: -1001,
    title: "ChatPulse Team",
    initials: "CT",
    timezone: "Europe/Kyiv",
    telegram_url: "https://t.me/chatpulse_team",
    status: { id: "active", label: "Активна", tone: "success" },
  },
  period: "week",
  pulse: {
    score: 82,
    label: "Активно",
    tone: "success",
    components: { messages: 90, members: 70, engagement: 80, continuity: 100 },
    positive: "Повідомлень стало на 18% більше.",
    negative: null,
  },
  personal_progress: {
    xp_total: 800,
    level: 4,
    tier: "Pulse",
    progress: 200,
    needed: 400,
    current_streak: 6,
    longest_streak: 10,
    protection_left: 3,
    rank: 2,
    rank_change: 1,
    period: group.period,
  },
  top_participants: [],
  insights: [
    {
      id: "steady",
      kind: "summary",
      icon: "activity",
      title: "Пульс тримається",
      description: "Група стабільна.",
    },
  ],
  top_message: null,
  popular_reaction: null,
  settings: {
    is_paused: false,
    weekly_reports_enabled: true,
    timezone: "Europe/Kyiv",
    report_weekday: 1,
    report_time: "19:00",
    report_card_theme: "dark_pulse",
    track_messages: true,
    track_media: true,
    track_replies: true,
    track_reactions: true,
  },
  capabilities: { is_admin: true },
};

const mockedApi = vi.mocked(api);
const mockedPremium = vi.mocked(usePremium);

afterEach(() => cleanup());

describe("GroupCenterPage", () => {
  it("loads Overview first and switches to an independently loaded Ranking tab", async () => {
    const user = userEvent.setup();
    mockedPremium.mockReturnValue({
      account: {
        plan: "free",
        is_owner: false,
        is_vip: false,
        vip_expires_at: null,
        entitlements: [],
      },
      trialAvailable: true,
      loading: false,
      has: () => false,
      refresh: vi.fn(),
      openVip: vi.fn(),
    });
    mockedApi.groupOverview.mockResolvedValue(overview);
    mockedApi.groupRanking.mockResolvedValue({
      metric: "xp",
      period: "week",
      rows: [],
      current_user: null,
    });

    render(<GroupCenterPage group={group} onBack={vi.fn()} />);

    expect(await screen.findByText("82")).toBeInTheDocument();
    expect(screen.getByText("Що нового")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Налаштування групи" })).toBeInTheDocument();

    await user.click(screen.getByRole("button", { name: /Рейтинг/ }));
    expect(await screen.findByText("Рейтинг учасників")).toBeInTheDocument();
    await waitFor(() => expect(mockedApi.groupRanking).toHaveBeenCalledWith(-1001, "xp", "week"));
  });

  it("keeps admin actions hidden when the server denies admin capability", async () => {
    mockedPremium.mockReturnValue({
      account: {
        plan: "free",
        is_owner: false,
        is_vip: false,
        vip_expires_at: null,
        entitlements: [],
      },
      trialAvailable: true,
      loading: false,
      has: () => false,
      refresh: vi.fn(),
      openVip: vi.fn(),
    });
    mockedApi.groupOverview.mockResolvedValue({
      ...overview,
      capabilities: { is_admin: false },
    });

    render(<GroupCenterPage group={{ ...group, is_admin: false }} onBack={vi.fn()} />);

    expect(await screen.findByText("82")).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Налаштування групи" })).not.toBeInTheDocument();
    expect(screen.queryByText("Швидкі дії адміністратора")).not.toBeInTheDocument();
  });
});
