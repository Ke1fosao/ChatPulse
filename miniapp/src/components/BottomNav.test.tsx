import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import "../styles/bottom-nav-v2.css";
import "../styles/global.css";
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
    expect(nav.querySelectorAll(":scope > .cp-bottom-nav__item")).toHaveLength(4);
    expect(container.querySelector(".bottom-nav__indicator")).not.toBeInTheDocument();
    expect(nav).toHaveClass("cp-bottom-nav--0");
    expect(nav).not.toHaveClass("bottom-nav");
    expect(screen.getByRole("button", { name: "Головна" })).toHaveAttribute(
      "aria-current",
      "page",
    );

    await user.click(screen.getByRole("button", { name: "Досягнення" }));
    expect(onChange).toHaveBeenCalledWith("achievements");

    rerender(<BottomNav active="achievements" onChange={onChange} />);
    expect(nav).toHaveClass("cp-bottom-nav--2");
    expect(nav.children).toHaveLength(4);
    expect(screen.getByRole("button", { name: "Досягнення" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("button", { name: "Головна" })).not.toHaveAttribute(
      "aria-current",
    );
  });

  it("keeps the final navigation layout at four equal slots after legacy global CSS loads", () => {
    const { container } = render(<BottomNav active="home" onChange={vi.fn()} />);

    const nav = container.querySelector<HTMLElement>(".cp-bottom-nav");
    const items = container.querySelectorAll<HTMLElement>(".cp-bottom-nav__item");

    expect(nav).not.toBeNull();
    expect(items).toHaveLength(4);

    const navStyle = getComputedStyle(nav!);
    const firstItemStyle = getComputedStyle(items[0]);

    expect(navStyle.display).toBe("flex");
    expect(navStyle.gridTemplateColumns).not.toContain("repeat(5");
    expect(firstItemStyle.width).toBe("25%");
    expect(firstItemStyle.maxWidth).toBe("25%");
  });
});
