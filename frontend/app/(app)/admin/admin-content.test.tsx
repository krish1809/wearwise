import { cleanup, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { api } from "@/lib/api/client";
import { apiAnswer, renderWithQueries } from "@/lib/test-utils";

import { AdminContent } from "./admin-content";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const STATS = {
  users: 12,
  new_users_7d: 3,
  demo_users: 4,
  items: 310,
  photos: 280,
  outfits: 41,
  wear_logs: 90,
  wear_logs_7d: 14,
  acceptance: [
    {
      engine_version: "1.2",
      shown: 200,
      liked: 30,
      saved: 12,
      worn: 9,
      accepted: 40,
    },
  ],
  ai_messages_today: 7,
  ai_images_today: 2,
  ai_spend_today_usd: 0.0123,
  ai_daily_cap_usd: 1,
  errors_24h: { server: 1, browser: 0 },
  recent_errors: [
    {
      id: "e1",
      created_at: "2026-10-21T08:00:00Z",
      source: "server",
      request_id: "abc12345",
      method: "GET",
      path: "/api/v1/items/{item_id}",
      status: 500,
      kind: "RuntimeError",
      message: "boom",
    },
  ],
};

it("shows the owner the counts, the acceptance rate, and recent errors", async () => {
  vi.spyOn(api, "GET").mockResolvedValue(apiAnswer(200, STATS) as never);
  renderWithQueries(<AdminContent />);

  expect(await screen.findByText("310")).toBeDefined();
  expect(screen.getByText("3 this week")).toBeDefined();
  expect(screen.getByText("40 (20%)")).toBeDefined();
  expect(screen.getByText(/ref abc12345/)).toBeDefined();
  expect(screen.getByText(/\$0\.0123 of the \$1\.00 daily cap/)).toBeDefined();
});

it("anyone else sees a page that isn't there", async () => {
  vi.spyOn(api, "GET").mockResolvedValue(
    apiAnswer(404, {
      error: { code: "not_found", message: "Not Found" },
    }) as never,
  );
  renderWithQueries(<AdminContent />);

  expect(await screen.findByText("Page not found")).toBeDefined();
  expect(screen.queryByText("Counts")).toBeNull();
});
