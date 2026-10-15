import { expect, it } from "vitest";

import { dayLabel, dayPhrase, isoDay, todayIso } from "@/lib/dates";

const NOW = new Date(2026, 9, 15, 23, 30); // 15 October 2026, late evening, local time

it("uses the local calendar day, even late at night", () => {
  expect(todayIso(NOW)).toBe("2026-10-15");
  expect(isoDay(new Date(2026, 0, 5))).toBe("2026-01-05");
});

it("names nearby days and dates the rest", () => {
  expect(dayLabel("2026-10-15", NOW)).toBe("Today");
  expect(dayLabel("2026-10-14", NOW)).toBe("Yesterday");
  // The exact punctuation comes from the browser's locale data, so check the parts.
  expect(dayLabel("2026-10-12", NOW)).toMatch(/^Mon,? 12 Oct$/);
  expect(dayLabel("2025-12-31", NOW)).toMatch(/^Wed,? 31 Dec,? 2025$/);
});

it("phrases days for the middle of a sentence", () => {
  expect(dayPhrase("2026-10-15", NOW)).toBe("today");
  expect(dayPhrase("2026-10-14", NOW)).toBe("yesterday");
  expect(dayPhrase("2026-10-12", NOW)).toMatch(/^on Mon,? 12 Oct$/);
});
