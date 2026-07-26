import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

function readStyle(name: string): string {
  return readFileSync(resolve(process.cwd(), "src/styles", name), "utf8");
}

describe("global CSS isolation", () => {
  it("does not contain obsolete unnamespaced bottom navigation selectors", () => {
    const globalCss = readStyle("global.css");
    expect(globalCss).not.toMatch(/(^|[,{\s])\.bottom-nav(?=[\s:{.#>])/m);
    expect(globalCss).not.toContain(".bottom-nav__item");
    expect(globalCss).not.toContain("grid-template-columns: repeat(5, 1fr)");
  });

  it("defines four equal namespaced navigation columns", () => {
    const navigationCss = readStyle("bottom-nav-stable.css");
    expect(navigationCss).toContain("grid-template-columns: repeat(4, minmax(0, 1fr))");
    expect(navigationCss).toContain("width: calc((100% - 12px) / 4)");
  });
});
