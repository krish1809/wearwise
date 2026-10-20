import {
  cleanup,
  fireEvent,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { useState } from "react";
import { afterEach, expect, it, vi } from "vitest";

import { REFERENCE } from "@/components/profile/test-data";
import { makeItem } from "@/components/wardrobe/test-data";
import { api } from "@/lib/api/client";
import type { Suggestion } from "@/lib/suggestions";
import { apiAnswer, renderWithQueries, sentBody } from "@/lib/test-utils";

import { SuggestionCard } from "./suggestion-card";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function brief(id: string, slot: string, display_name: string) {
  const item = makeItem({ id, slot, display_name });
  return {
    id: item.id,
    display_name: item.display_name,
    category_id: item.category_id,
    slot: item.slot,
    color_primary: item.color_primary,
    color_hex: item.color_hex,
    status: item.status,
    archived: false,
    photo: null,
  };
}

function makeSuggestion(overrides: Partial<Suggestion> = {}): Suggestion {
  return {
    id: "sug-1",
    kind: "occasion",
    template_id: "separates",
    occasion_id: "college",
    season: "mild",
    score: 0.86,
    compromise: false,
    engine_version: "1.0",
    pieces: [
      { slot: "top", item: brief("shirt", "top", "White shirt"), core: true },
      {
        slot: "bottom",
        item: brief("chinos", "bottom", "Beige chinos"),
        core: true,
      },
      {
        slot: "footwear",
        item: brief("loafers", "footwear", "Brown loafers"),
        core: true,
      },
    ],
    reasons: [
      {
        code: "color.neutrals",
        kind: "positive",
        text: "White shirt and beige chinos: neutrals with clear contrast.",
      },
      {
        code: "rotation.just_worn",
        kind: "caution",
        text: "You wore the brown loafers in the last two days.",
      },
    ],
    rating: null,
    saved_outfit_id: null,
    worn_on: null,
    stale: false,
    ...overrides,
  };
}

function Harness({ initial }: { initial: Suggestion }) {
  const [suggestion, setSuggestion] = useState(initial);
  return (
    <SuggestionCard
      suggestion={suggestion}
      slots={REFERENCE.slots.map((slot, position) => ({ ...slot, position }))}
      familyHex={new Map()}
      occasionName="College / everyday"
      onChange={setSuggestion}
    />
  );
}

it("names the outfit and gives its reasons, cautions marked", () => {
  renderWithQueries(<Harness initial={makeSuggestion()} />);

  expect(
    screen.getByRole("heading", {
      name: "White shirt, beige chinos and brown loafers",
    }),
  ).toBeDefined();
  expect(screen.getByText("For college / everyday")).toBeDefined();
  expect(
    screen.getByText(/neutrals with clear contrast/).textContent,
  ).not.toContain("Worth knowing");
  expect(screen.getByText(/Worth knowing/).parentElement?.textContent).toBe(
    "Worth knowing: You wore the brown loafers in the last two days.",
  );
});

it("likes a suggestion, and a second tap takes the like back", async () => {
  const post = vi
    .spyOn(api, "POST")
    .mockResolvedValue(
      apiAnswer(200, makeSuggestion({ rating: "like" })) as never,
    );
  const remove = vi
    .spyOn(api, "DELETE")
    .mockResolvedValue(apiAnswer(200, makeSuggestion()) as never);
  renderWithQueries(<Harness initial={makeSuggestion()} />);

  fireEvent.click(screen.getByRole("button", { name: /^Like / }));
  const liked = await screen.findByRole("button", { name: /^Like / });
  await waitFor(() => expect(liked.getAttribute("aria-pressed")).toBe("true"));
  expect(sentBody(post)).toEqual({ verdict: "like" });

  fireEvent.click(liked);
  await waitFor(() =>
    expect(
      screen
        .getByRole("button", { name: /^Like / })
        .getAttribute("aria-pressed"),
    ).toBe("false"),
  );
  expect(remove).toHaveBeenCalledOnce();
});

it("asks which piece when a dislike is about one piece", async () => {
  const post = vi
    .spyOn(api, "POST")
    .mockResolvedValue(
      apiAnswer(200, makeSuggestion({ rating: "dislike" })) as never,
    );
  renderWithQueries(<Harness initial={makeSuggestion()} />);

  fireEvent.click(screen.getByRole("button", { name: /^Dislike / }));
  const dialog = await screen.findByRole("dialog");
  fireEvent.click(
    within(dialog).getByRole("radio", {
      name: "I don't like one of the pieces",
    }),
  );
  fireEvent.click(within(dialog).getByRole("button", { name: "Dislike" }));
  expect(
    await within(dialog).findByText("Choose the piece you don't like."),
  ).toBeDefined();
  expect(post).not.toHaveBeenCalled();

  fireEvent.click(within(dialog).getByRole("radio", { name: "Brown loafers" }));
  fireEvent.click(within(dialog).getByRole("button", { name: "Dislike" }));

  await waitFor(() => expect(screen.queryByRole("dialog")).toBeNull());
  expect(sentBody(post)).toEqual({
    verdict: "dislike",
    reason: "item",
    item_id: "loafers",
  });
});

it("saves the suggestion and links to the saved outfit", async () => {
  const post = vi
    .spyOn(api, "POST")
    .mockResolvedValue(apiAnswer(201, { id: "outfit-9" }) as never);
  renderWithQueries(<Harness initial={makeSuggestion()} />);

  fireEvent.click(screen.getByRole("button", { name: "Save outfit" }));

  const link = await screen.findByRole("link", { name: /view outfit/ });
  expect(link.getAttribute("href")).toBe("/outfits/outfit-9");
  expect(post.mock.calls[0][0]).toBe(
    "/api/v1/suggestions/{suggestion_id}/save",
  );
});

it("explains instead of offering actions once a piece has gone", () => {
  renderWithQueries(<Harness initial={makeSuggestion({ stale: true })} />);

  expect(screen.getByText(/deleted or archived since/)).toBeDefined();
  expect(screen.queryByRole("button", { name: "Save outfit" })).toBeNull();
});
