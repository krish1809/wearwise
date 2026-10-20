import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { makeProfile, REFERENCE } from "@/components/profile/test-data";
import { makeAnalysis, makeCandidate } from "@/components/shopping/test-data";
import { api } from "@/lib/api/client";
import {
  apiAnswer,
  renderWithQueries,
  sentBody,
  typeInto,
} from "@/lib/test-utils";

import { CandidateView } from "./candidate-view";

const nav = vi.hoisted(() => ({ push: vi.fn(), replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useParams: () => ({ id: "c1" }),
  useRouter: () => nav,
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  nav.push.mockReset();
});

function show(analysis: unknown, status = 200) {
  vi.spyOn(api, "GET").mockImplementation(async (path) => {
    if (path === "/api/v1/candidates/{candidate_id}")
      return apiAnswer(200, makeCandidate()) as never;
    if (path === "/api/v1/candidates/{candidate_id}/analysis")
      return apiAnswer(status, analysis) as never;
    if (path === "/api/v1/reference") return apiAnswer(200, REFERENCE) as never;
    if (path === "/api/v1/profile")
      return apiAnswer(200, makeProfile()) as never;
    if (path === "/api/v1/categories") return apiAnswer(200, []) as never;
    return apiAnswer(404, {}) as never;
  });
  renderWithQueries(<CandidateView />);
}

it("shows the verdict, its reasons, and the numbers behind it", async () => {
  show(makeAnalysis());

  expect(await screen.findByText("Buy")).toBeDefined();
  expect(
    screen.getByText(
      "It gives you a first good outfit for college / everyday in winter.",
    ),
  ).toBeDefined();
  expect(screen.getByText("Similar to your black chinos.")).toBeDefined();
  expect(screen.getByText("₹300")).toBeDefined();
  expect(screen.getByText("Black chinos, 71% alike")).toBeDefined();
  // Coverage: a gap that opens reads "None to 3"; a full cell stays "10+".
  expect(screen.getByRole("cell", { name: "None to 3" })).toBeDefined();
  expect(screen.getByRole("cell", { name: "10+" })).toBeDefined();
  expect(screen.getByText("Goes with 1 thing you own")).toBeDefined();
});

it("asks for occasions when the analysis needs them", async () => {
  show(
    { error: { code: "needs_occasions", message: "Choose the occasions" } },
    409,
  );

  expect(
    await screen.findByText(/Choose the occasions you dress for/),
  ).toBeDefined();
});

it("buying it sends the price paid in paise and opens the new item", async () => {
  show(makeAnalysis());
  const post = vi
    .spyOn(api, "POST")
    .mockResolvedValue(apiAnswer(201, { item_id: "item-9" }) as never);

  fireEvent.click(await screen.findByRole("button", { name: "I bought it" }));
  typeInto("Price paid, in rupees (optional)", "1650");
  fireEvent.click(screen.getByRole("button", { name: "Add to wardrobe" }));

  await vi.waitFor(() =>
    expect(nav.push).toHaveBeenCalledWith("/wardrobe/item-9"),
  );
  expect(sentBody(post)).toMatchObject({ price: 165000 });
});
