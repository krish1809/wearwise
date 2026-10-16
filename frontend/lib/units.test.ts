import { describe, expect, it } from "vitest";

import { fromCm, parseNumber, rangeIn, toCm } from "@/lib/units";

describe("unit conversion", () => {
  it("converts known values both ways", () => {
    expect(toCm(1, "in")).toBe(2.5);
    expect(toCm(32, "in")).toBe(81.3);
    expect(fromCm(81.28, "in")).toBe(32);
    expect(fromCm(96, "in")).toBe(37.8);
    expect(toCm(96, "cm")).toBe(96);
    expect(fromCm(81.25, "cm")).toBe(81.3);
  });

  it("shows the same inches after saving any value typed in inches", () => {
    for (let tenths = 100; tenths <= 1000; tenths += 1) {
      const typed = tenths / 10;
      expect(fromCm(toCm(typed, "in"), "in")).toBe(typed);
    }
  });

  it("keeps any value typed in cm exactly", () => {
    for (let tenths = 250; tenths <= 2500; tenths += 1) {
      const typed = tenths / 10;
      expect(fromCm(toCm(typed, "cm"), "cm")).toBe(typed);
    }
  });

  it("keeps a range in inches inside the range in cm", () => {
    const [low, high] = rangeIn([50, 200], "in");

    expect([low, high]).toEqual([19.7, 78.7]);
    expect(toCm(low, "in")).toBeGreaterThanOrEqual(50);
    expect(toCm(high, "in")).toBeLessThanOrEqual(200);
    expect(rangeIn([50, 200], "cm")).toEqual([50, 200]);
  });
});

describe("parseNumber", () => {
  it("reads numbers, blanks, and mistakes", () => {
    expect(parseNumber(" 81.5 ")).toBe(81.5);
    expect(parseNumber("81,5")).toBe(81.5);
    expect(parseNumber("")).toBeNull();
    expect(parseNumber("8l")).toBeNaN();
    expect(parseNumber("-3")).toBeNaN();
  });
});
