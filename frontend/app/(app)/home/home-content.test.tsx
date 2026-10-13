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

function showHome(profile: Profile) {
  vi.spyOn(api, "GET").mockImplementation(async (path) =>
    path === "/api/v1/profile"
      ? (apiAnswer(200, profile) as never)
      : (apiAnswer(200, USER) as never),
  );
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
