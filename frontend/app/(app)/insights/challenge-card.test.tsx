import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { brief } from "@/components/shopping/test-data";
import { api } from "@/lib/api/client";
import { apiAnswer, renderWithQueries } from "@/lib/test-utils";

import { ChallengeCard } from "./challenge-card";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const RUNNING = {
  started_on: "2026-10-20",
  ends_on: "2026-12-18",
  day: 1,
  days: 60,
  finished: false,
  total: 4,
  worn: 1,
  unworn: [brief("tee", "Olive T-shirt"), brief("chinos", "Navy chinos")],
  unworn_count: 3,
};

it("starts the challenge and shows progress from the wear log", async () => {
  vi.spyOn(api, "GET").mockResolvedValue(
    apiAnswer(200, { challenge: null, days: 60 }) as never,
  );
  const post = vi
    .spyOn(api, "POST")
    .mockResolvedValue(
      apiAnswer(200, { challenge: RUNNING, days: 60 }) as never,
    );
  renderWithQueries(<ChallengeCard familyHex={new Map()} />);

  fireEvent.click(
    await screen.findByRole("button", { name: "Start the challenge" }),
  );

  expect(await screen.findByText(/Day 1 of 60/)).toBeDefined();
  expect(post).toHaveBeenCalledWith("/api/v1/insights/challenge");
  const bar = screen.getByRole("progressbar", { name: "Pieces worn" });
  expect(bar.getAttribute("aria-valuenow")).toBe("1");
  expect(bar.getAttribute("aria-valuemax")).toBe("4");
  expect(screen.getByRole("link", { name: "Olive T-shirt" })).toBeDefined();
  expect(screen.getByText("and 1 more")).toBeDefined();
});

it("says how it went once it's over, and offers to start again", async () => {
  vi.spyOn(api, "GET").mockResolvedValue(
    apiAnswer(200, {
      challenge: {
        ...RUNNING,
        day: 62,
        finished: true,
        worn: 4,
        unworn: [],
        unworn_count: 0,
      },
      days: 60,
    }) as never,
  );
  renderWithQueries(<ChallengeCard familyHex={new Map()} />);

  expect(
    await screen.findByText(/You wore 4 of 4 pieces in 60 days\./),
  ).toBeDefined();
  expect(
    screen.getByText("Every piece has been worn. Well done."),
  ).toBeDefined();
  expect(screen.getByRole("button", { name: "Start again" })).toBeDefined();
});
