import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import { BottomNav } from "./BottomNav";

vi.mock("../telegram/sdk", () => ({
  haptic: vi.fn(),
}));

describe("BottomNav", () => {
  it("renders exactly four equal navigation children and animates the active position", async () => {
    const user = userEvent.setup();
    const onChange = vi.fn();
    const { rerender, container } = render(
      <BottomNav active="home" onChange={onChange} />,
    );

    const nav = screen.getByRole("navigation", { name: "Основна навігація" });
    expect(screen.getAllByRole("button")).toHaveLength(4);
    expect(nav.children).toHaveLength(4);
    expect(nav.querySelectorAll(":scope > .bottom-nav__item")).toHaveLength(4);
    expect(container.querySelector(".bottom-nav__indicator")).not.toBeInTheDocument();
    expect(nav).toHaveClass("bottom-nav--0");
    expect(screen.getByRole("button", { name: "Головна" })).toHaveAttribute(
      "aria-current",
      "page",
    );

    await user.click(screen.getByRole("button", { name: "Досягнення" }));
    expect(onChange).toHaveBeenCalledWith("achievements");

    rerender(<BottomNav active="achievements" onChange={onChange} />);
    expect(nav).toHaveClass("bottom-nav--2");
    expect(nav.children).toHaveLength(4);
    expect(screen.getByRole("button", { name: "Досягнення" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("button", { name: "Головна" })).not.toHaveAttribute(
      "aria-current",
    );
  });
});
