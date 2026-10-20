import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { REFERENCE } from "@/components/profile/test-data";
import { makeItem } from "@/components/wardrobe/test-data";
import { api } from "@/lib/api/client";
import { apiAnswer, renderWithQueries, sentBody } from "@/lib/test-utils";

import { makeCandidate } from "./test-data";
import { TryOn } from "./try-on";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const SHIRT = makeItem({
  id: "shirt",
  slot: "top",
  display_name: "White shirt",
});
const LOAFERS = makeItem({
  id: "loafers",
  slot: "footwear",
  display_name: "Brown loafers",
});

function open() {
  vi.spyOn(api, "GET").mockImplementation(async (_path, init) => {
    const slot = (init as { params: { query: { slot: string[] } } }).params
      .query.slot[0];
    const items = { top: [SHIRT], footwear: [LOAFERS] }[slot] ?? [];
    return apiAnswer(200, {
      items,
      next_cursor: null,
      total: items.length,
    }) as never;
  });
  const post = vi.spyOn(api, "POST").mockImplementation((async (
    _path: string,
    init?: { body?: { item_ids: string[] } },
  ) => {
    const ids = init?.body?.item_ids ?? [];
    const whole = ids.includes("shirt") && ids.includes("loafers");
    return apiAnswer(
      200,
      whole
        ? {
            complete: true,
            score: 0.74,
            good: true,
            reasons: [
              {
                code: "colour.neutral",
                kind: "positive",
                text: "Navy and white sit easily together.",
              },
            ],
            message: null,
          }
        : {
            complete: false,
            score: null,
            good: null,
            reasons: [],
            message: "Still needed: footwear.",
          },
    );
  }) as never);
  renderWithQueries(
    <TryOn
      candidate={makeCandidate()}
      reference={REFERENCE}
      occasionIds={["college"]}
    />,
  );
  return post;
}

it("scores the candidate with the pieces you add, and offers only slots that fit", async () => {
  const post = open();

  // The candidate is a bottom: no bottoms or one-pieces to add.
  expect(screen.queryByRole("button", { name: "Bottom" })).toBeNull();
  expect(screen.queryByRole("button", { name: "One-piece" })).toBeNull();

  fireEvent.click(
    await screen.findByRole("button", { name: "Add: White shirt" }),
  );
  expect(await screen.findByText("Still needed: footwear.")).toBeDefined();

  fireEvent.click(screen.getByRole("button", { name: "Footwear" }));
  fireEvent.click(
    await screen.findByRole("button", { name: "Add: Brown loafers" }),
  );

  const meter = await screen.findByRole("meter", { name: "Outfit score" });
  expect(meter.getAttribute("aria-valuenow")).toBe("74");
  expect(screen.getByText("Navy and white sit easily together.")).toBeDefined();
  await waitFor(() =>
    expect(sentBody(post, post.mock.calls.length - 1)).toEqual({
      item_ids: ["loafers", "shirt"],
      occasion_id: "college",
    }),
  );
});
