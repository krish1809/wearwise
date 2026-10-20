import {
  cleanup,
  fireEvent,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { REFERENCE } from "@/components/profile/test-data";
import { makeItem } from "@/components/wardrobe/test-data";
import { api } from "@/lib/api/client";
import { apiAnswer, renderWithQueries, sentBody } from "@/lib/test-utils";

import { OutfitStudio } from "./outfit-studio";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const SHIRT = makeItem({
  id: "shirt",
  slot: "top",
  display_name: "Navy casual shirt",
});
const CHINOS = makeItem({
  id: "chinos",
  slot: "bottom",
  display_name: "Olive chinos",
  color_primary: "olive",
});
const LOAFERS = makeItem({
  id: "loafers",
  slot: "footwear",
  display_name: "Brown loafers",
});
const WATCH = makeItem({
  id: "watch",
  slot: "watch",
  display_name: "Steel watch",
});
const BY_SLOT: Record<string, (typeof SHIRT)[]> = {
  top: [SHIRT],
  bottom: [CHINOS],
  footwear: [LOAFERS],
  watch: [WATCH],
};

function check(ids: string[]) {
  const missing = ["top", "bottom", "footwear"].filter(
    (slot) => !ids.includes(BY_SLOT[slot][0].id),
  );
  return {
    complete: missing.length === 0,
    template_id: "separates",
    template_name: "Top and bottom",
    missing,
    missing_names: missing.map((slot) => slot[0].toUpperCase() + slot.slice(1)),
    misplaced_item_ids: [],
    crowded: [],
    optional_slots: ["layer", "belt", "watch", "fragrance"],
    message: missing.length ? `Still needed: ${missing.join(", ")}.` : null,
  };
}

function open() {
  vi.spyOn(api, "GET").mockImplementation(async (_path, init) => {
    const slot = (init as { params: { query: { slot: string[] } } }).params
      .query.slot[0];
    return apiAnswer(200, {
      items: BY_SLOT[slot] ?? [],
      next_cursor: null,
      total: 1,
    }) as never;
  });
  vi.spyOn(api, "POST").mockImplementation((async (
    _path: string,
    init?: { body?: { item_ids: string[] } },
  ) => apiAnswer(200, check(init?.body?.item_ids ?? []))) as never);
  const onSave = vi.fn(async () => {});
  renderWithQueries(
    <OutfitStudio reference={REFERENCE} saving={false} onSave={onSave} />,
  );
  return onSave;
}

async function choose(slot: string, item: string) {
  fireEvent.click(screen.getByRole("button", { name: `Choose ${slot}` }));
  const dialog = await screen.findByRole("dialog");
  fireEvent.click(
    await within(dialog).findByRole("button", { name: new RegExp(item) }),
  );
  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
}

it("says what's still needed as pieces are chosen", async () => {
  open();

  expect(
    await screen.findByText("Start with a top or a one-piece."),
  ).toBeDefined();
  await choose("top", "Navy casual shirt");

  expect(
    await screen.findByText("Still needed: bottom, footwear."),
  ).toBeDefined();
  await choose("bottom", "Olive chinos");
  await choose("footwear", "Brown loafers");
  expect(
    await screen.findByText("Ready to save: top and bottom."),
  ).toBeDefined();
});

it("offers finishing touches the outfit can take", async () => {
  open();
  await choose("top", "Navy casual shirt");

  const touches = await screen.findByRole("button", { name: "Watch" });
  expect(screen.getByRole("button", { name: "Fragrance" })).toBeDefined();
  fireEvent.click(touches);
  const dialog = await screen.findByRole("dialog");
  fireEvent.click(
    await within(dialog).findByRole("button", { name: /Steel watch/ }),
  );

  expect(
    await screen.findByRole("button", { name: "Change watch" }),
  ).toBeDefined();
  expect(screen.queryByRole("button", { name: "Watch" })).toBeNull();
});

it("saves the chosen pieces with the details", async () => {
  const onSave = open();
  await choose("top", "Navy casual shirt");
  await choose("bottom", "Olive chinos");
  await choose("footwear", "Brown loafers");

  fireEvent.change(screen.getByLabelText("Name (optional)"), {
    target: { value: " Friday " },
  });
  fireEvent.change(screen.getByLabelText("Occasion (optional)"), {
    target: { value: "college" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Save outfit" }));

  await waitFor(() =>
    expect(onSave).toHaveBeenCalledWith(
      {
        item_ids: ["shirt", "chinos", "loafers"],
        name: "Friday",
        occasion_id: "college",
        is_favorite: false,
      },
      // Built by hand, not from a suggestion.
      undefined,
    ),
  );
  expect(sentBody(vi.mocked(api.POST), 0)).toEqual({ item_ids: [] });
});

it("completes the outfit from a suggestion and saves it as that suggestion", async () => {
  vi.spyOn(api, "GET").mockImplementation(async (_path, init) => {
    const slot = (init as { params: { query: { slot: string[] } } }).params
      .query.slot[0];
    return apiAnswer(200, {
      items: BY_SLOT[slot] ?? [],
      next_cursor: null,
      total: 1,
    }) as never;
  });
  const asBrief = (item: typeof SHIRT) => ({
    id: item.id,
    display_name: item.display_name,
    category_id: item.category_id,
    slot: item.slot,
    color_primary: item.color_primary,
    color_hex: item.color_hex,
    status: item.status,
    archived: false,
    photo: null,
  });
  const post = vi.spyOn(api, "POST").mockImplementation((async (
    path: string,
    init?: { body?: { item_ids: string[] } },
  ) =>
    path === "/api/v1/outfits/suggest"
      ? apiAnswer(200, {
          suggestions: [
            {
              id: "sug-7",
              kind: "with_item",
              template_id: "separates",
              occasion_id: null,
              season: "mild",
              score: 0.8,
              compromise: false,
              engine_version: "1.0",
              pieces: [SHIRT, CHINOS, LOAFERS].map((item) => ({
                slot: item.slot,
                item: asBrief(item),
                core: true,
              })),
              reasons: [
                {
                  code: "formality.match",
                  kind: "positive",
                  text: "Every piece sits at the same level of dress.",
                },
              ],
              rating: null,
              saved_outfit_id: null,
              worn_on: null,
              stale: false,
            },
          ],
          missing: [],
          compromise: false,
          note: null,
          season: "mild",
          engine_version: "1.0",
        })
      : apiAnswer(200, check(init?.body?.item_ids ?? []))) as never);
  const onSave = vi.fn(async () => {});
  renderWithQueries(
    <OutfitStudio reference={REFERENCE} saving={false} onSave={onSave} />,
  );
  await choose("top", "Navy casual shirt");

  fireEvent.click(screen.getByRole("button", { name: "Complete this outfit" }));
  const dialog = await screen.findByRole("dialog");
  expect(
    await within(dialog).findByText(
      "Every piece sits at the same level of dress.",
    ),
  ).toBeDefined();
  expect(
    (post.mock.calls as unknown[][]).find(
      ([path]) => path === "/api/v1/outfits/suggest",
    )?.[1],
  ).toEqual({
    body: { occasion_id: null, anchor_item_ids: ["shirt"], count: 4 },
  });
  fireEvent.click(within(dialog).getByRole("button", { name: /^Use / }));

  expect(
    await screen.findByText("Ready to save: top and bottom."),
  ).toBeDefined();
  fireEvent.click(screen.getByRole("button", { name: "Save outfit" }));
  await waitFor(() => expect(onSave).toHaveBeenCalledOnce());
  expect(onSave).toHaveBeenCalledWith(
    expect.objectContaining({ item_ids: ["shirt", "chinos", "loafers"] }),
    "sug-7",
  );
});
