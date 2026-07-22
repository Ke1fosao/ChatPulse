import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { GroupCardData } from "../api/types";
import { GroupCard } from "./GroupCard";

const baseGroup: GroupCardData = {
  telegram_chat_id: -1001,
  title: "ChatPulse Team",
  initials: "CT",
  level: 4,
  xp_total: 850,
  current_streak: 6,
  rank: 2,
  period: {
    messages_count: 120,
    media_count: 8,
    replies_count: 30,
    reactions_received: 40,
    photo_count: 5,
    voice_count: 3,
    night_messages_count: 2,
    morning_messages_count: 7,
    xp_earned: 180,
    active_members: 9,
  },
  trend: 12,
  is_admin: false,
  last_activity_at: "2026-07-22T10:00:00Z",
};

afterEach(cleanup);

describe("GroupCard", () => {
  it("shows a clear admin status and management hint for administrator groups", () => {
    render(<GroupCard group={{ ...baseGroup, is_admin: true }} onOpen={vi.fn()} />);

    expect(screen.getByText("Ви адміністратор")).toBeInTheDocument();
    expect(screen.getByText("Доступне керування групою")).toBeInTheDocument();
  });

  it("does not show admin controls for ordinary member groups", () => {
    render(<GroupCard group={baseGroup} onOpen={vi.fn()} />);

    expect(screen.queryByText("Ви адміністратор")).not.toBeInTheDocument();
    expect(screen.queryByText("Доступне керування групою")).not.toBeInTheDocument();
  });
});
