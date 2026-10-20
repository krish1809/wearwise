import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { makeProfile, REFERENCE } from "@/components/profile/test-data";
import { makeItem } from "@/components/wardrobe/test-data";
import { api } from "@/lib/api/client";
import type { Profile } from "@/lib/profile";
import { apiAnswer, renderWithQueries } from "@/lib/test-utils";

import { HomeContent } from "./home-content";

const USER = {
  id: "1",
  email: "sam@example.com",
  name: "Sam Lee",
  onboarding_completed: true,
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function planDay(pieces: unknown[] = []) {
  return {
    day: "2026-10-20",
    occasion_id: "college",
    occasion_source: "usual",
    events: [],
    weather: { source: "forecast", feels_like: 31.4, rain_chance: 20 },
    pieces,
    reasons: [],
    score: pieces.length ? 0.8 : null,
    missing: [],
    locked: false,
    worn: false,
    outdated: false,
    stale: false,
    unavailable: [],
  };
}

const NO_INSIGHTS = {
  items: 0,
  logs: 0,
  days_logged_30: 0,
  needed_logs: 5,
  enough: false,
  most_worn: [],
  least_worn: [],
  by_month: [],
  by_group: [],
  by_color: [],
  cheapest: [],
  dearest: [],
  needs_price: [],
  versatile: null,
  orphans: null,
  coverage: null,
  style: null,
  declutter: [],
  engine_version: "1.1",
};

function showHome(
  profile: Profile,
  todaysLogs: unknown[] = [],
  today = planDay(),
  insights: unknown = NO_INSIGHTS,
) {
  vi.spyOn(api, "GET").mockImplementation(async (path) => {
    if (path === "/api/v1/profile") return apiAnswer(200, profile) as never;
    if (path === "/api/v1/reference") return apiAnswer(200, REFERENCE) as never;
    if (path === "/api/v1/wear-logs") {
      return apiAnswer(200, { logs: todaysLogs, next_cursor: null }) as never;
    }
    if (path === "/api/v1/insights") return apiAnswer(200, insights) as never;
    if (path === "/api/v1/plan") {
      return apiAnswer(200, {
        start: today.day,
        days: [today],
        laundry_weekday: null,
        engine_version: "1.1",
      }) as never;
    }
    return apiAnswer(200, USER) as never;
  });
  renderWithQueries(<HomeContent />);
}

it("offers to finish setting up after onboarding was skipped", async () => {
  const post = vi.spyOn(api, "POST").mockResolvedValue(apiAnswer(204) as never);
  showHome(makeProfile({ show_onboarding_reminder: true }));

  expect(await screen.findByText("Finish setting up WearWise")).toBeDefined();
  expect(
    screen.getByRole("link", { name: "Finish setup" }).getAttribute("href"),
  ).toBe("/onboarding");

  fireEvent.click(screen.getByRole("button", { name: "Not now" }));

  await waitFor(() =>
    expect(screen.queryByText("Finish setting up WearWise")).toBeNull(),
  );
  expect(post).toHaveBeenCalledWith("/api/v1/onboarding/reminder/dismiss");
});

it("says nothing about setup otherwise", async () => {
  showHome(makeProfile());

  expect(await screen.findByText("Hello, Sam")).toBeDefined();
  expect(screen.queryByText("Finish setting up WearWise")).toBeNull();
});

it("nudges to log today's outfit when nothing is logged", async () => {
  showHome(makeProfile());

  expect(await screen.findByText(/Nothing logged for today yet/)).toBeDefined();
  expect(
    screen.getByRole("link", { name: "Plan my week" }).getAttribute("href"),
  ).toBe("/week");
  expect(
    screen
      .getByRole("link", { name: "Suggest an outfit" })
      .getAttribute("href"),
  ).toBe("/outfits/suggest");
  expect(
    await screen.findByText("Feels like 31°, 20% chance of rain"),
  ).toBeDefined();
});

it("shows the outfit planned for today, ready to mark as worn", async () => {
  const brief = (id: string, slot: string, display_name: string) => {
    const item = makeItem({ id, slot, display_name });
    return {
      slot,
      core: true,
      item: {
        id,
        display_name,
        category_id: item.category_id,
        slot,
        color_primary: item.color_primary,
        color_hex: null,
        status: "available",
        archived: false,
        photo: null,
      },
    };
  };
  showHome(
    makeProfile(),
    [],
    planDay([
      brief("shirt", "top", "White shirt"),
      brief("chinos", "bottom", "Beige chinos"),
      brief("loafers", "footwear", "Brown loafers"),
    ]),
  );

  expect(
    await screen.findByText(
      "Planned: White shirt, beige chinos and brown loafers.",
    ),
  ).toBeDefined();
  expect(screen.getByRole("button", { name: "I wore this" })).toBeDefined();
});

it("says what was worn today", async () => {
  const piece = (name: string) => ({
    slot: "top",
    item: null,
    name,
    removed: false,
  });
  showHome(makeProfile(), [
    {
      id: "log-1",
      worn_on: "2026-10-15",
      outfit_id: null,
      outfit_name: null,
      occasion_id: null,
      note: null,
      pieces: [
        piece("Navy casual shirt"),
        piece("Olive chinos"),
        piece("Brown loafers"),
      ],
      created_at: "2026-10-15T08:00:00Z",
    },
  ]);

  expect(
    await screen.findByText(
      "You wore Navy casual shirt, olive chinos and brown loafers.",
    ),
  ).toBeDefined();
});

it("shares one fact from the insights", async () => {
  showHome(makeProfile(), [], planDay(), {
    ...NO_INSIGHTS,
    items: 3,
    needs_price: [{ id: "a" }, { id: "b" }],
  });

  expect(
    await screen.findByText(
      "2 worn pieces have no price, so there's no cost per wear yet.",
    ),
  ).toBeDefined();
  expect(
    screen.getByRole("link", { name: "See all insights" }).getAttribute("href"),
  ).toBe("/insights");
});
