import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BottomNav } from "./BottomNav";

vi.mock("../telegram/sdk", () => ({
  haptic: vi.fn(),
}));

describe("BottomNav", () => {
  it("renders four items and moves the shared indicator with the active tab", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const { rerender, container } = render(
      <BottomNav active="home" onChange={onChange} />,
    );

    expect(screen.getAllByRole("button")).toHaveLength(4);
    expect(screen.queryByRole("button", { name: "Рейтинг" })).not.toBeInTheDocument();
    expect(container.querySelector(".bottom-nav__indicator")).toBeInTheDocument();
    expect(container.querySelector(".bottom-nav")).toHaveStyle("--active-index: 0");

    await user.click(screen.getByRole("button", { name: "Досягнення" }));
    expect(onChange).toHaveBeenCalledWith("achievements");

    rerender(<BottomNav active="achievements" onChange={onChange} />);
    expect(container.querySelector(".bottom-nav")).toHaveStyle("--active-index: 2");
    expect(screen.getByRole("button", { name: "Досягнення" })).toHaveAttribute(
      "aria-current",
      "page",
    );
  });
});
