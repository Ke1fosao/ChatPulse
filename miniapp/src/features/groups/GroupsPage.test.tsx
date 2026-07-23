import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { GroupsV2CardData } from "../../api/groups-v2";
import { GroupsPage } from "./GroupsPage";

const groups: GroupsV2CardData[] = [
  {
    telegram_chat_id: -1,
    title: "Активна команда",
    initials: "АК",
    level: 4,
    xp_total: 900,
    current_streak: 5,
    rank: 2,
    period: {
      messages_count: 40,
      media_count: 2,
      replies_count: 7,
      reactions_received: 12,
      photo_count: 1,
      voice_count: 1,
      night_messages_count: 0,
      morning_messages_count: 4,
      xp_earned: 180,
      active_members: 5,
    },
    trend: 24,
    is_admin: true,
    last_activity_at: "2026-07-23T12:00:00+00:00",
    status: { id: "active", label: "Активна", tone: "success", attention_reason: null },
    is_favorite: false,
    bot_operational: true,
    messages_today: 12,
    messages_7d: 40,
    attention_reason: null,
  },
  {
    telegram_chat_id: -2,
    title: "Потрібне налаштування",
    initials: "ПН",
    level: 1,
    xp_total: 10,
    current_streak: 0,
    rank: null,
    period: {
      messages_count: 0,
      media_count: 0,
      replies_count: 0,
      reactions_received: 0,
      photo_count: 0,
      voice_count: 0,
      night_messages_count: 0,
      morning_messages_count: 0,
      xp_earned: 0,
      active_members: 0,
    },
    trend: null,
    is_admin: false,
    last_activity_at: "2026-07-10T12:00:00+00:00",
    status: {
      id: "needs_setup",
      label: "Потрібне налаштування",
      tone: "warning",
      attention_reason: "Надайте права адміністратора.",
    },
    is_favorite: true,
    bot_operational: false,
    messages_today: 0,
    messages_7d: 0,
    attention_reason: "Надайте права адміністратора.",
  },
];

afterEach(() => cleanup());

describe("GroupsPage", () => {
  it("shows the compact summary and filters groups by status", async () => {
    const user = userEvent.setup();
    render(
      <GroupsPage
        groups={groups}
        onOpenGroup={vi.fn()}
        onToggleFavorite={vi.fn()}
        onRefresh={vi.fn()}
      />,
    );

    expect(screen.getByText("2", { selector: ".groups-summary strong" })).toBeInTheDocument();
    await user.click(screen.getByRole("button", { name: "Активні" }));
    expect(screen.getByText("Активна команда")).toBeInTheDocument();
    expect(screen.queryByText("Надайте права адміністратора.")).not.toBeInTheDocument();
  });

  it("toggles favorite without opening the group", async () => {
    const user = userEvent.setup();
    const openGroup = vi.fn();
    const toggleFavorite = vi.fn();
    render(
      <GroupsPage
        groups={groups}
        onOpenGroup={openGroup}
        onToggleFavorite={toggleFavorite}
        onRefresh={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("button", { name: "Додати Активна команда в обране" }));
    expect(toggleFavorite).toHaveBeenCalledWith(groups[0], true);
    expect(openGroup).not.toHaveBeenCalled();
  });
});
