import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { api } from "@/lib/api/client";
import { apiAnswer, renderWithQueries } from "@/lib/test-utils";

import { PicksContent } from "./picks-content";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const SHIRT = {
  id: "i1",
  display_name: "White casual shirt",
  category_id: "casual_shirt",
  slot: "top",
  color_primary: "white",
  color_hex: "#F5F5F2",
  status: "available",
  archived: false,
  photo: null,
};

const PICK = {
  id: "p1",
  position: 0,
  kind: "buy",
  trend_name: "Olive chinos",
  trend_summary: "Olive chinos, everywhere this season.",
  name: "Olive cotton chinos",
  category_id: "chinos",
  color_primary: "olive",
  color_hex: "#6B6B3A",
  text: "Olive cotton chinos would make 4 new outfits with what you own.",
  verdict: "consider",
  new_outfits: 4,
  reasons: [
    { code: "verdict.outfits", kind: "positive", text: "Makes 4 new outfits." },
  ],
  items: [SHIRT],
  query: "Olive cotton chinos men",
  links: [
    {
      shop_id: "myntra",
      shop: "Myntra",
      url: "https://www.myntra.com/olive-cotton-chinos-men?rawQuery=Olive%20cotton%20chinos%20men",
    },
  ],
  usual_spend: 150000,
  not_for_me: false,
};

const DIGEST = {
  id: "d1",
  week: "2026-W43",
  status: "built",
  note: null,
  season: "mild",
  subject: "Worth a look this week: olive cotton chinos",
  intro:
    "What's in fashion in India this mild, judged against what you already own.",
  worked_out_at: "2026-10-21T10:00:00Z",
  sent_at: null,
  picks: [PICK],
};

function answers(latest: unknown, status = 200) {
  return vi
    .spyOn(api, "GET")
    .mockImplementation(((path: string) =>
      Promise.resolve(
        path === "/api/v1/reference"
          ? apiAnswer(200, { color_families: [] })
          : apiAnswer(status, latest),
      )) as never);
}

it("shows each pick with its reasons, the person's own pieces, and where to look", async () => {
  answers(DIGEST);
  renderWithQueries(<PicksContent />);

  expect(await screen.findByText("Olive cotton chinos")).toBeDefined();
  expect(screen.getByText("Worth a look")).toBeDefined();
  expect(screen.getByText(PICK.text)).toBeDefined();
  expect(screen.getByText("Makes 4 new outfits.")).toBeDefined();
  expect(
    screen.getByRole("link", { name: "White casual shirt" }),
  ).toBeDefined();
  expect(screen.getByText(/you usually spend up to ₹1,500/)).toBeDefined();
  const shop = screen.getByRole("link", { name: /Myntra/ });
  expect(shop.getAttribute("href")).toBe(PICK.links[0]?.url);
  expect(shop.getAttribute("rel")).toBe("noopener noreferrer");
});

it("before any picks it offers to work them out, without an email", async () => {
  answers(
    { error: { code: "no_digest", message: "No weekly picks yet." } },
    404,
  );
  const post = vi
    .spyOn(api, "POST")
    .mockResolvedValue(apiAnswer(200, DIGEST) as never);
  renderWithQueries(<PicksContent />);

  fireEvent.click(
    await screen.findByRole("button", { name: "Show this week's picks" }),
  );

  await waitFor(() =>
    expect(post).toHaveBeenCalledWith("/api/v1/digests/preview"),
  );
  expect(await screen.findByText("Olive cotton chinos")).toBeDefined();
});

it("not for me is marked on the pick and can be undone", async () => {
  answers(DIGEST);
  const post = vi.spyOn(api, "POST").mockResolvedValue(
    apiAnswer(200, {
      ...DIGEST,
      picks: [{ ...PICK, not_for_me: true }],
    }) as never,
  );
  renderWithQueries(<PicksContent />);

  fireEvent.click(await screen.findByRole("button", { name: "Not for me" }));

  await waitFor(() => expect(post).toHaveBeenCalledOnce());
  expect(post.mock.calls[0]?.[0]).toBe(
    "/api/v1/digest-picks/{pick_id}/not-for-me",
  );
  expect(await screen.findByText(/Marked not for me/)).toBeDefined();
  expect(screen.getByRole("button", { name: "Undo" })).toBeDefined();
});

it("with nothing worth buying it says so plainly", async () => {
  answers({
    ...DIGEST,
    status: "nothing",
    subject: "Nothing worth buying this week",
    note: "Nothing in fashion now would add much to what you own. That's a good week to buy nothing.",
    picks: [],
  });
  renderWithQueries(<PicksContent />);

  expect(
    await screen.findByText("Nothing worth buying this week"),
  ).toBeDefined();
  expect(screen.getByText(/good week to buy nothing/)).toBeDefined();
});
