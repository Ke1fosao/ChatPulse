import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BottomNav } from "./BottomNav";

vi.mock("../telegram/sdk", () => ({
  haptic: vi.fn(),
}));

describe("BottomNav", () => {
  it("renders four navigation items and marks only the active tab", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const { rerender, container } = render(
      <BottomNav active="home" onChange={onChange} />,
    );

    expect(screen.getAllByRole("button")).toHaveLength(4);
    expect(container.querySelectorAll(".bottom-nav__item")).toHaveLength(4);
    expect(container.querySelector(".bottom-nav__indicator")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Головна" })).toHaveAttribute(
      "aria-current",
      "page",
    );

    await user.click(screen.getByRole("button", { name: "Досягнення" }));
    expect(onChange).toHaveBeenCalledWith("achievements");

    rerender(<BottomNav active="achievements" onChange={onChange} />);
    expect(screen.getByRole("button", { name: "Досягнення" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("button", { name: "Головна" })).not.toHaveAttribute(
      "aria-current",
    );
  });
});
