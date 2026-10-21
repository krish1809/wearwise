import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { api } from "@/lib/api/client";
import { apiAnswer, renderWithQueries, sentBody } from "@/lib/test-utils";

import { TrendsContent } from "./trends-content";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const TREND = {
  id: "t1",
  name: "Linen co-ord sets",
  summary: "Matching linen shirts and trousers.",
  why_now: "Warm afternoons.",
  status: "pending",
  first_seen_at: "2026-10-20T00:10:00Z",
  last_seen_at: "2026-10-21T00:10:00Z",
  decided_at: null,
  categories: [{ id: "co_ord_set", name: "Co-ord set (worn as one)" }],
  colors: [{ id: "sage", name: "Sage", hex: "#9CAF88" }],
  fabrics: [{ id: "linen", name: "Linen" }],
  patterns: [],
  fits: [],
  seasons: [],
  sections: [{ id: "menswear", name: "Menswear" }],
  styles: [],
  sources: [
    {
      url: "https://style-one.example/linen",
      domain: "style-one.example",
      title: "Linen co-ords for easy days",
      published_on: "2026-10-18",
      quote: "linen co-ord sets in sage and beige",
    },
    {
      url: "javascript:alert(1)",
      domain: "bad.example",
      title: "Not a web page",
      published_on: "2026-10-17",
      quote: "anything",
    },
  ],
};

const LIST = {
  trends: [TREND],
  counts: { pending: 1, approved: 4, rejected: 0, expired: 2 },
};

it("shows each waiting trend with its sources, quotes, and colours", async () => {
  vi.spyOn(api, "GET").mockResolvedValue(apiAnswer(200, LIST) as never);
  renderWithQueries(<TrendsContent />);

  expect(await screen.findByText("Linen co-ord sets")).toBeDefined();
  expect(screen.getByText("Why now: Warm afternoons.")).toBeDefined();
  expect(screen.getByText("Co-ord set (worn as one)")).toBeDefined();
  expect(screen.getByText("Sage")).toBeDefined();
  expect(screen.getByText(/linen co-ord sets in sage and beige/)).toBeDefined();
  const link = screen.getByRole("link", {
    name: "Linen co-ords for easy days",
  });
  expect(link.getAttribute("href")).toBe("https://style-one.example/linen");
  expect(link.getAttribute("rel")).toBe("noopener noreferrer");
  // An address that isn't a web page is shown, never made a link.
  expect(screen.queryByRole("link", { name: "Not a web page" })).toBeNull();
  expect(screen.getByRole("tab", { name: "Approved (4)" })).toBeDefined();
});

it("approving sends the decision and says what it means", async () => {
  vi.spyOn(api, "GET").mockResolvedValue(apiAnswer(200, LIST) as never);
  const patch = vi
    .spyOn(api, "PATCH")
    .mockResolvedValue(
      apiAnswer(200, { ...TREND, status: "approved" }) as never,
    );
  renderWithQueries(<TrendsContent />);

  fireEvent.click(await screen.findByRole("button", { name: "Approve" }));

  await waitFor(() => expect(patch).toHaveBeenCalledOnce());
  expect(sentBody(patch)).toEqual({ status: "approved" });
  expect(patch.mock.calls[0]?.[0]).toBe("/api/v1/admin/trends/{trend_id}");
});

it("anyone else sees a page that isn't there", async () => {
  vi.spyOn(api, "GET").mockResolvedValue(
    apiAnswer(404, {
      error: { code: "not_found", message: "Not Found" },
    }) as never,
  );
  renderWithQueries(<TrendsContent />);

  expect(await screen.findByText("Page not found")).toBeDefined();
  expect(screen.queryByText("Trends")).toBeNull();
});
