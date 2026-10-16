import { expect, it } from "vitest";

import { formatRupees, paiseToRupeesText, rupeesToPaise } from "@/lib/money";

it("turns typed rupees into whole paise", () => {
  expect(rupeesToPaise("1500")).toBe(150000);
  expect(rupeesToPaise(" 1,500.50 ")).toBe(150050);
  expect(rupeesToPaise("0.1")).toBe(10);
  expect(rupeesToPaise("")).toBeNull();
  expect(rupeesToPaise("-5")).toBeNaN();
  expect(rupeesToPaise("12.345")).toBeNaN();
});

it("shows paise as rupees", () => {
  expect(paiseToRupeesText(150000)).toBe("1500");
  expect(paiseToRupeesText(150050)).toBe("1500.5");
  expect(paiseToRupeesText(null)).toBe("");
  expect(formatRupees(150000)).toBe("₹1,500");
  expect(formatRupees(10000000)).toBe("₹1,00,000");
});
