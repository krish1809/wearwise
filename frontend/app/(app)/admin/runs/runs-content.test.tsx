import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { api } from "@/lib/api/client";
import { apiAnswer, renderWithQueries } from "@/lib/test-utils";

import { RunsContent } from "./runs-content";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const RUN = {
  id: "r1",
  kind: "trend_scout",
  trigger: "schedule",
  status: "stopped",
  started_at: "2026-10-21T00:11:00Z",
  finished_at: "2026-10-21T00:11:42Z",
  search_credits: 6,
  tokens_in: 12000,
  tokens_out: 900,
  cost_micro_usd: 1700,
  stopped_by: "search_credits",
  errors: ["search refused: festive footwear trends India 2026"],
  steps: {
    plan_queries: {
      planned_by: "model",
      queries: ["men's linen trends India 2026"],
    },
    search: { searched: 6, failed: 1, results: 30, credits: 6 },
    read: { read: 12, skipped: { "no date": 2, "blocked site": 5 } },
    validate: {
      kept: 1,
      dropped: [{ name: "Gold bags", reason: "fewer than two sites" }],
    },
    save: { added: ["Linen co-ord sets"], merged: [] },
  },
};

it("shows each run: how it ended, what it spent, and what it did", async () => {
  vi.spyOn(api, "GET").mockResolvedValue(
    apiAnswer(200, {
      runs: [RUN],
      credits_this_month: 24,
      credit_cap: 600,
    }) as never,
  );
  renderWithQueries(<RunsContent />);

  expect(await screen.findByText("Stopped early")).toBeDefined();
  expect(
    screen.getByText("Stopped early: the month's search credits ran out."),
  ).toBeDefined();
  expect(
    screen.getByText(/6 search credits · 12,900 tokens · about \$0\.0017/),
  ).toBeDefined();
  expect(
    screen.getByText("24 of 600 search credits used this month."),
  ).toBeDefined();
  expect(screen.getByText("men's linen trends India 2026")).toBeDefined();
  // Most skipped reason first, whatever order the database kept.
  expect(
    screen.getByText(/Not read: blocked site \(5\), no date \(2\)/),
  ).toBeDefined();
  expect(
    screen.getByText("Dropped Gold bags: fewer than two sites"),
  ).toBeDefined();
  expect(screen.getByText("New: Linen co-ord sets")).toBeDefined();
});

it("before the first run it says where runs come from", async () => {
  vi.spyOn(api, "GET").mockResolvedValue(
    apiAnswer(200, {
      runs: [],
      credits_this_month: 0,
      credit_cap: 600,
    }) as never,
  );
  renderWithQueries(<RunsContent />);

  expect(await screen.findByText(/No runs yet/)).toBeDefined();
});

it("the weekly email's runs show their counts, never who", async () => {
  const EMAIL_RUN = {
    ...RUN,
    id: "r2",
    kind: "weekly_digest",
    status: "done",
    stopped_by: null,
    errors: [],
    search_credits: 0,
    steps: {
      send: {
        due: 3,
        sent: 2,
        wording_model: 2,
        held_by_daily_cap: 1,
        over_cap: 0,
      },
    },
  };
  vi.spyOn(api, "GET").mockImplementation(((
    _path: string,
    options: { params: { query: { kind: string } } },
  ) =>
    Promise.resolve(
      apiAnswer(200, {
        runs:
          options.params.query.kind === "weekly_digest" ? [EMAIL_RUN] : [RUN],
        credits_this_month: 24,
        credit_cap: 600,
      }),
    )) as never);
  renderWithQueries(<RunsContent />);

  await screen.findByText("Stopped early");
  fireEvent.mouseDown(screen.getByRole("tab", { name: "Weekly email" }));
  fireEvent.click(screen.getByRole("tab", { name: "Weekly email" }));

  expect(await screen.findByText("2 sent")).toBeDefined();
  expect(screen.getByText("1 held: the day's email limit")).toBeDefined();
  expect(screen.queryByText(/search credits used this month/)).toBeNull();
});
