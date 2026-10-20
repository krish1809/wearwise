import { cleanup, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { makeProfile, REFERENCE } from "@/components/profile/test-data";
import { api } from "@/lib/api/client";
import type { Insights } from "@/lib/insights";
import { apiAnswer, renderWithQueries } from "@/lib/test-utils";

import { InsightsContent } from "./insights-content";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function brief(id: string, display_name: string) {
  return {
    id,
    display_name,
    category_id: "casual_shirt",
    slot: "top",
    color_primary: "navy",
    color_hex: null,
    status: "available",
    archived: false,
    photo: null,
  };
}

const SHIRT = brief("shirt", "White shirt");
const LOAFERS = brief("loafers", "Brown loafers");

function makeInsights(overrides: Partial<Insights> = {}): Insights {
  return {
    items: 6,
    logs: 5,
    days_logged_30: 3,
    needed_logs: 5,
    enough: true,
    most_worn: [{ item: LOAFERS, wears: 5, last_worn_on: "2026-10-19" }],
    least_worn: [{ item: SHIRT, wears: 0, last_worn_on: null }],
    by_month: [
      { month: "2026-09", days: 2 },
      { month: "2026-10", days: 3 },
    ],
    by_group: [{ id: "tops", name: "Tops", wears: 5 }],
    by_color: [{ id: "navy", name: "Navy", wears: 2, hex: "#1F2A44" }],
    cheapest: [
      {
        item: SHIRT,
        price: 150000,
        currency: "INR",
        wears: 3,
        per_wear: 50000,
      },
    ],
    dearest: [],
    needs_price: [LOAFERS],
    versatile: [{ item: SHIRT, outfits: 4 }],
    orphans: [
      {
        item: LOAFERS,
        outfits: 0,
        rescue:
          "Nothing you have for the bottom suits it; a plain white one would.",
      },
    ],
    coverage: {
      occasion_ids: ["college"],
      seasons: ["summer", "winter"],
      cells: [
        { occasion_id: "college", season: "summer", outfits: 10, capped: true },
        { occasion_id: "college", season: "winter", outfits: 0, capped: false },
      ],
    },
    style: null,
    declutter: [],
    engine_version: "1.1",
    ...overrides,
  };
}

function show(insights: Insights) {
  vi.spyOn(api, "GET").mockImplementation(async (path) => {
    if (path === "/api/v1/insights") return apiAnswer(200, insights) as never;
    if (path === "/api/v1/reference") return apiAnswer(200, REFERENCE) as never;
    if (path === "/api/v1/profile")
      return apiAnswer(200, makeProfile()) as never;
    if (path === "/api/v1/categories") return apiAnswer(200, []) as never;
    return apiAnswer(404, {}) as never;
  });
  renderWithQueries(<InsightsContent />);
}

it("shows wear, value, versatility, and coverage from the numbers given", async () => {
  show(makeInsights());

  expect(
    await screen.findByText(/6 items · 5 days of wear logged/),
  ).toBeDefined();
  const value = screen.getByText("Best value").closest("div") as HTMLElement;
  expect(within(value).getByText("₹500")).toBeDefined();
  expect(within(value).getByText("₹1,500 ÷ 3")).toBeDefined();
  expect(
    screen
      .getByRole("link", { name: "Add a price for Brown loafers" })
      .getAttribute("href"),
  ).toBe("/wardrobe/loafers/edit");
  expect(
    screen.getByText(
      "Nothing you have for the bottom suits it; a plain white one would.",
    ),
  ).toBeDefined();
  expect(screen.getByText("10+")).toBeDefined();
  expect(screen.getByText("None")).toBeDefined();
});

it("asks for more days before ranking anything", async () => {
  show(makeInsights({ logs: 2, enough: false, most_worn: [], least_worn: [] }));

  expect(
    await screen.findByText(/Log what you wear on 3 more days/),
  ).toBeDefined();
  expect(screen.queryByText("Most worn")).toBeNull();
});

it("asks for occasions before counting outfits", async () => {
  show(makeInsights({ coverage: null, versatile: null, orphans: null }));

  expect(
    await screen.findByText(/Choose the occasions you dress for/),
  ).toBeDefined();
  expect(screen.queryByText("Most versatile")).toBeNull();
});
