import { cleanup, fireEvent, screen, within } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { makeProfile, REFERENCE } from "@/components/profile/test-data";
import { makeCandidate, makeGaps } from "@/components/shopping/test-data";
import { api } from "@/lib/api/client";
import type { Gaps } from "@/lib/shopping";
import { apiAnswer, renderWithQueries, sentBody } from "@/lib/test-utils";

import { ShoppingContent } from "./shopping-content";

vi.mock("next/navigation", () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn() }),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function show(gaps: Gaps, candidates = [makeCandidate()]) {
  vi.spyOn(api, "GET").mockImplementation(async (path) => {
    if (path === "/api/v1/shopping/gaps") return apiAnswer(200, gaps) as never;
    if (path === "/api/v1/candidates")
      return apiAnswer(200, { candidates, needs_occasions: false }) as never;
    if (path === "/api/v1/reference") return apiAnswer(200, REFERENCE) as never;
    if (path === "/api/v1/profile")
      return apiAnswer(200, makeProfile()) as never;
    if (path === "/api/v1/categories") return apiAnswer(200, []) as never;
    return apiAnswer(404, {}) as never;
  });
  renderWithQueries(<ShoppingContent />);
}

it("shows what would add most and puts a staple on the list", async () => {
  show(makeGaps());
  const post = vi
    .spyOn(api, "POST")
    .mockResolvedValue(
      apiAnswer(201, makeCandidate({ id: "c2", source: "archetype" })) as never,
    );

  expect(
    await screen.findByText(
      "4 new good outfits, for college / everyday in every season.",
    ),
  ).toBeDefined();
  fireEvent.click(
    screen.getByRole("button", { name: "Add to list: White sneakers" }),
  );

  await vi.waitFor(() => expect(post).toHaveBeenCalled());
  expect(post.mock.calls[0]?.[0]).toBe("/api/v1/candidates/from-staple");
  expect(sentBody(post)).toEqual({ archetype_id: "white_sneakers" });
});

it("groups the list by where each stands, with its verdict and dated price", async () => {
  show(makeGaps({ gaps: [], covered: true }), [
    makeCandidate({
      id: "a",
      display_name: "Navy chinos",
      verdict: "buy",
      status: "buy_next",
    }),
    makeCandidate({
      id: "b",
      display_name: "Olive tee",
      verdict: null,
      price: null,
    }),
  ]);

  const next = (await screen.findByText("Buy next"))
    .parentElement as HTMLElement;
  expect(within(next).getByText("Navy chinos")).toBeDefined();
  expect(within(next).getByText("Buy")).toBeDefined();
  expect(within(next).getByText(/₹1,800/)).toBeDefined();
  expect(within(next).getByText(/noted on/)).toBeDefined();
  expect(screen.getByText("Not checked yet")).toBeDefined();
  expect(
    screen.getByText(
      "Every occasion and season you dress for already has plenty of good outfits.",
    ),
  ).toBeDefined();
});

it("asks for occasions before working out gaps", async () => {
  show(makeGaps({ needs_occasions: true, gaps: [] }));

  expect(
    await screen.findByText(/Choose the occasions you dress for/),
  ).toBeDefined();
});
