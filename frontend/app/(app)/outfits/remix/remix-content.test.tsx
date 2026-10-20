import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { REFERENCE } from "@/components/profile/test-data";
import { brief } from "@/components/shopping/test-data";
import { makeItem } from "@/components/wardrobe/test-data";
import { api } from "@/lib/api/client";
import { apiAnswer, renderWithQueries, sentBody } from "@/lib/test-utils";

import { RemixContent } from "./remix-content";

vi.mock("@/components/wardrobe/wardrobe-data", async (original) => ({
  ...(await original<typeof import("@/components/wardrobe/wardrobe-data")>()),
  WardrobeData: ({
    children,
  }: {
    children: (data: { reference: typeof REFERENCE }) => React.ReactNode;
  }) => children({ reference: REFERENCE }),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const SHIRT = makeItem({
  id: "shirt",
  slot: "top",
  display_name: "White shirt",
});
const TEE = makeItem({ id: "tee", slot: "top", display_name: "Olive T-shirt" });
const CHINOS = makeItem({
  id: "chinos",
  slot: "bottom",
  display_name: "Navy chinos",
});

it("finds the good outfits the chosen pieces make, per occasion", async () => {
  vi.spyOn(api, "GET").mockImplementation(async (_path, init) => {
    const slot = (init as { params: { query: { slot: string[] } } }).params
      .query.slot[0];
    const items = { top: [SHIRT, TEE], bottom: [CHINOS] }[slot] ?? [];
    return apiAnswer(200, {
      items,
      next_cursor: null,
      total: items.length,
    }) as never;
  });
  const post = vi.spyOn(api, "POST").mockResolvedValue(
    apiAnswer(200, {
      season: "mild",
      total: 1,
      needs_occasions: false,
      groups: [
        {
          occasion_id: "college",
          occasion_name: "College",
          count: 1,
          outfits: [
            {
              items: [
                brief("shirt", "White shirt"),
                brief("chinos", "Navy chinos", "bottom"),
              ],
              score: 0.8,
            },
          ],
        },
      ],
    }) as never,
  );
  renderWithQueries(<RemixContent />);

  fireEvent.click(
    await screen.findByRole("button", { name: "Add: White shirt" }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Add: Olive T-shirt" }));
  // Pressed again, it comes out.
  fireEvent.click(
    screen.getByRole("button", { name: "Chosen: Olive T-shirt" }),
  );
  expect(
    screen.getByText("Choose at least two pieces", { exact: false }),
  ).toBeDefined();
  fireEvent.click(screen.getByRole("button", { name: "Bottom" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Add: Navy chinos" }),
  );

  expect(
    await screen.findByText("1 good outfit from 2 pieces, for mild weather."),
  ).toBeDefined();
  expect(screen.getByText("White shirt, Navy chinos")).toBeDefined();
  // Live, like the studio's score: the latest pieces are what's asked about.
  await waitFor(() =>
    expect(sentBody(post, post.mock.calls.length - 1)).toEqual({
      item_ids: ["chinos", "shirt"],
    }),
  );
});
