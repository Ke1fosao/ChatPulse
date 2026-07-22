import { cleanup, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import type { GroupSettings } from "../../api/types";
import { GroupSettingsPanel } from "./GroupSettingsPanel";

const settings: GroupSettings = {
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
};

afterEach(cleanup);

describe("GroupSettingsPanel", () => {
  it("saves a changed field immediately without a global save button", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockResolvedValue({ ...settings, track_messages: false });

    render(
      <GroupSettingsPanel
        settings={settings}
        onSave={onSave}
        onReset={vi.fn().mockResolvedValue(undefined)}
        onBack={vi.fn()}
      />,
    );

    await user.click(screen.getByRole("checkbox", { name: "Повідомлення" }));

    await waitFor(() => expect(onSave).toHaveBeenCalledWith({ track_messages: false }));
    expect(screen.queryByRole("button", { name: /Зберегти зміни/ })).not.toBeInTheDocument();
    expect(await screen.findByText("Збережено")).toBeInTheDocument();
  });

  it("restores the server value when autosave fails", async () => {
    const user = userEvent.setup();
    const onSave = vi.fn().mockRejectedValue(new Error("Немає доступу"));

    render(
      <GroupSettingsPanel
        settings={settings}
        onSave={onSave}
        onReset={vi.fn().mockResolvedValue(undefined)}
        onBack={vi.fn()}
      />,
    );

    const checkbox = screen.getByRole("checkbox", { name: "Повідомлення" });
    await user.click(checkbox);

    expect(await screen.findByText("Немає доступу")).toBeInTheDocument();
    expect(checkbox).toBeChecked();
  });

  it("has a dedicated back action for the full settings screen", () => {
    const onBack = vi.fn();
    render(
      <GroupSettingsPanel
        settings={settings}
        onSave={vi.fn().mockResolvedValue(settings)}
        onReset={vi.fn().mockResolvedValue(undefined)}
        onBack={onBack}
      />,
    );

    expect(screen.getByRole("button", { name: "Назад до групи" })).toBeInTheDocument();
    expect(screen.getByText("Налаштування групи")).toBeInTheDocument();
  });
});
