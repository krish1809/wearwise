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
  ])("%s goes to %s", (next, expected) => {
    expect(safeNextPath(next)).toBe(expected);
  });
});
