import { describe, expect, it } from "vitest";

import { safeNextPath } from "@/lib/auth";

describe("safeNextPath", () => {
  it.each([
    ["/settings", "/settings"],
    ["/home?tab=week", "/home?tab=week"],
    [null, "/home"],
    ["", "/home"],
    ["https://elsewhere.example", "/home"],
    ["//elsewhere.example", "/home"],
    ["/\\elsewhere.example", "/home"],
    // Browsers drop tabs and line breaks, which would turn these into "//elsewhere".
    ["/\t/elsewhere.example", "/home"],
    ["/\n/elsewhere.example", "/home"],
    ["/\\/elsewhere.example", "/home"],
    ["/wardrobe#top", "/wardrobe#top"],
  ])("%s goes to %s", (next, expected) => {
    expect(safeNextPath(next)).toBe(expected);
  });
});
