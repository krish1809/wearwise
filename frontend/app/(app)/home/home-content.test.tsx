import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { makeProfile } from "@/components/profile/test-data";
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

function showHome(profile: Profile, todaysLogs: unknown[] = []) {
  vi.spyOn(api, "GET").mockImplementation(async (path) => {
    if (path === "/api/v1/profile") return apiAnswer(200, profile) as never;
    if (path === "/api/v1/wear-logs") {
      return apiAnswer(200, { logs: todaysLogs, next_cursor: null }) as never;
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
    screen.getByRole("link", { name: "Choose an outfit" }).getAttribute("href"),
  ).toBe("/outfits");
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
