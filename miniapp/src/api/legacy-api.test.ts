import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";


describe("canonical Mini App client", () => {
  it("does not expose removed dashboard, rankings, or legacy profile-card paths", () => {
    const source = readFileSync(resolve(import.meta.dirname, "client.ts"), "utf8");
    expect(source).not.toContain("group: (chatId");
    expect(source).not.toContain("rankings: (chatId");
    expect(source).not.toContain("/groups/${chatId}/rankings");
    expect(source).not.toContain('requestBlob("/profile-card")');
    expect(source).toContain('request<{ groups: GroupsV2CardData[] }>("/groups-v2"');
    expect(source).toContain("/profile-card-showcase");
  });
});
