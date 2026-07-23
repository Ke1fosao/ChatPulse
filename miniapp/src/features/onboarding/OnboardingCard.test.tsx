import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import type { OnboardingPayload } from "../../api/types";
import { OnboardingCard } from "./OnboardingCard";

const incomplete: OnboardingPayload = {
  completed_steps: 1,
  total_steps: 3,
  is_complete: false,
  add_group_url: "https://t.me/chatpulse_bot?startgroup=true",
  primary_action: "add_group",
  linked_group: null,
  steps: [
    { id: "start", title: "Запусти ChatPulse", description: "Готово", completed: true },
    { id: "group", title: "Додай у групу", description: "Додай бота", completed: false },
    {
      id: "activity",
      title: "Створи перший пульс",
      description: "Напиши повідомлення",
      completed: false,
    },
  ],
};

describe("OnboardingCard", () => {
  it("shows progress and opens the next Telegram action", () => {
    const openLink = vi.fn();
    render(<OnboardingCard onboarding={incomplete} onOpenTelegramLink={openLink} />);

    expect(screen.getByText("1 із 3")).toBeInTheDocument();
    expect(screen.getByText("Додай у групу")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "Додати в групу" }));
    expect(openLink).toHaveBeenCalledWith(incomplete.add_group_url);
  });

  it("renders nothing after onboarding is complete", () => {
    const { container } = render(
      <OnboardingCard
        onboarding={{ ...incomplete, completed_steps: 3, is_complete: true }}
        onOpenTelegramLink={vi.fn()}
      />,
    );
    expect(container).toBeEmptyDOMElement();
  });
});
