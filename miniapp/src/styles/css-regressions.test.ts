import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const stylesDirectory = fileURLToPath(new URL("./", import.meta.url));

function readStyle(name: string): string {
  return readFileSync(new URL(name, `file://${stylesDirectory}`), "utf8");
}

describe("global CSS isolation", () => {
  it("does not contain the obsolete unnamespaced bottom navigation selectors", () => {
    const globalCss = readStyle("global.css");

    expect(globalCss).not.toMatch(/(^|[,{\s])\.bottom-nav(?=[\s:{.#>])/m);
    expect(globalCss).not.toContain(".bottom-nav-item");
    expect(globalCss).not.toContain("grid-template-columns: repeat(5, 1fr)");
  });
});
