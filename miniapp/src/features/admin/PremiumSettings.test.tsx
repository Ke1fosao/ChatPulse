import { cleanup, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, expect, it, vi } from "vitest";
import type { GroupSettings } from "../../api/types";
import { usePremium } from "../../premium/PremiumContext";
import { GroupSettingsPanel } from "./GroupSettingsPanel";

vi.mock("../../premium/PremiumContext", () => ({ usePremium: vi.fn() }));
const mockedPremium = vi.mocked(usePremium);

const settings = {
  is_paused: false,
  weekly_reports_enabled: true,
  timezone: "Europe/Kyiv",
  report_weekday: 6,
  report_time: "19:30",
  report_card_theme: "dark_pulse",
  track_messages: true,
  track_media: true,
  track_replies: true,
  track_reactions: true,
} as GroupSettings;

afterEach(() => cleanup());

it("opens contextual VIP when a free admin selects a premium theme", async () => {
  const user = userEvent.setup();
  const openVip = vi.fn();
  mockedPremium.mockReturnValue({
    account: { plan: "free", is_owner: false, is_vip: false, vip_expires_at: null, entitlements: [] },
    trialAvailable: true,
    loading: false,
    has: () => false,
    refresh: vi.fn(),
    openVip,
  });
  render(
    <GroupSettingsPanel
      chatId={-1001}
      settings={settings}
      onSave={vi.fn().mockResolvedValue(settings)}
      onReset={vi.fn().mockResolvedValue(undefined)}
      onBack={vi.fn()}
    />,
  );

  await user.selectOptions(screen.getByLabelText("Тема звіту"), "telegram_wave");
  expect(openVip).toHaveBeenCalledWith("group_settings_theme", "reports.premium_themes");
});
