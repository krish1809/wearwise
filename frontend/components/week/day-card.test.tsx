import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { REFERENCE } from "@/components/profile/test-data";
import { api } from "@/lib/api/client";
import { isoDay, todayIso } from "@/lib/dates";
import type { PlanDay } from "@/lib/plan";
import { apiAnswer, renderWithQueries, sentBody } from "@/lib/test-utils";

import { DayCard } from "./day-card";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function piece(id: string, slot: string, display_name: string) {
  return {
    slot,
    core: true,
    item: {
      id,
      display_name,
      category_id: "tshirt",
      slot,
      color_primary: "navy",
      color_hex: null,
      status: "available",
      archived: false,
      photo: null,
    },
  };
}

function makeDay(overrides: Partial<PlanDay> = {}): PlanDay {
  return {
    day: todayIso(),
    occasion_id: "college",
    occasion_source: "usual",
    events: [],
    weather: { source: "forecast", feels_like: 29.6, rain_chance: 40 },
    pieces: [
      piece("shirt", "top", "White shirt"),
      piece("chinos", "bottom", "Beige chinos"),
      piece("loafers", "footwear", "Brown loafers"),
    ],
    reasons: [
      {
        code: "formality.match",
        kind: "positive",
        text: "Every piece sits at the same level of dress.",
      },
    ],
    score: 0.82,
    missing: [],
    locked: false,
    worn: false,
    outdated: false,
    stale: false,
    unavailable: [],
    ...overrides,
  };
}

function show(day: PlanDay) {
  renderWithQueries(
    <DayCard
      day={day}
      start={todayIso()}
      reference={REFERENCE}
      usualName="College / everyday"
      slots={REFERENCE.slots.map((slot, position) => ({ ...slot, position }))}
      familyHex={new Map()}
    />,
  );
}

it("shows the day's weather, usual occasion, outfit, and reasons", () => {
  show(makeDay());

  expect(screen.getByRole("heading", { name: "Today" })).toBeDefined();
  expect(screen.getByText(/Feels like 30°, 40% chance of rain/)).toBeDefined();
  expect(
    screen.getByRole("option", { name: "Usual: College / everyday" }),
  ).toBeDefined();
  expect(
    screen.getByText("White shirt, beige chinos and brown loafers"),
  ).toBeDefined();
  expect(
    screen.getByText("Every piece sits at the same level of dress."),
  ).toBeDefined();
  expect(screen.getByRole("button", { name: "I wore this" })).toBeDefined();
});

it("locks the day", async () => {
  const patch = vi
    .spyOn(api, "PATCH")
    .mockResolvedValue(apiAnswer(200, makeDay({ locked: true })) as never);
  show(makeDay());

  fireEvent.click(screen.getByRole("button", { name: "Lock Today" }));

  await waitFor(() => expect(patch).toHaveBeenCalledOnce());
  expect(sentBody(patch)).toEqual({ locked: true });
});

it("says why nothing is planned", () => {
  show(
    makeDay({
      pieces: [],
      reasons: [],
      missing: ["There's no footwear in your wardrobe yet."],
    }),
  );

  expect(
    screen.getByText("There's no footwear in your wardrobe yet."),
  ).toBeDefined();
  expect(screen.queryByRole("button", { name: "I wore this" })).toBeNull();
});

it("flags a day planned for an old occasion and pieces in the laundry", () => {
  show(makeDay({ outdated: true, unavailable: ["White shirt"] }));

  expect(screen.getByText(/Planned for a different occasion/)).toBeDefined();
  expect(
    screen.getByText("Not available right now: White shirt."),
  ).toBeDefined();
});

it("offers to mark only today or earlier as worn", () => {
  const later = new Date();
  later.setDate(later.getDate() + 2);

  show(makeDay({ day: isoDay(later) }));

  expect(screen.queryByRole("button", { name: "I wore this" })).toBeNull();
  expect(screen.getByRole("button", { name: /Swap the outfit/ })).toBeDefined();
});
