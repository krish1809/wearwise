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

function swipe(target: HTMLElement, dx: number, dy = 0, pointerType = "touch") {
  fireEvent.pointerDown(target, {
    pointerType,
    pointerId: 1,
    clientX: 100,
    clientY: 100,
  });
  fireEvent.pointerMove(target, {
    pointerType,
    pointerId: 1,
    clientX: 100 + dx,
    clientY: 100 + dy,
  });
  fireEvent.pointerUp(target, { pointerType, pointerId: 1 });
}

function board(): HTMLElement {
  return screen.getByRole("group", { name: /swipe right to like/ });
}

it("a swipe sends exactly what the buttons send", async () => {
  const post = vi
    .spyOn(api, "POST")
    .mockResolvedValue(apiAnswer(200, makeSuggestion()) as never);

  // The buttons: Like, then Dislike with no reason given.
  renderWithQueries(<Harness initial={makeSuggestion()} />);
  fireEvent.click(screen.getByRole("button", { name: /^Like / }));
  await waitFor(() => expect(post).toHaveBeenCalledTimes(1));
  fireEvent.click(screen.getByRole("button", { name: /^Dislike / }));
  const dialog = await screen.findByRole("dialog");
  fireEvent.click(within(dialog).getByRole("button", { name: "Dislike" }));
  await waitFor(() => expect(post).toHaveBeenCalledTimes(2));
  cleanup();

  // The same two by swiping.
  renderWithQueries(<Harness initial={makeSuggestion()} />);
  swipe(board(), 150);
  await waitFor(() => expect(post).toHaveBeenCalledTimes(3));
  swipe(board(), -150);
  await waitFor(() => expect(post).toHaveBeenCalledTimes(4));

  expect(sentBody(post, 2)).toEqual(sentBody(post, 0));
  expect(sentBody(post, 3)).toEqual(sentBody(post, 1));
  expect(sentBody(post, 2)).toEqual({ verdict: "like" });
  expect(sentBody(post, 3)).toEqual({
    verdict: "dislike",
    reason: null,
    item_id: null,
  });
});

it("an accidental swipe can be undone", async () => {
  vi.spyOn(api, "POST").mockResolvedValue(
    apiAnswer(200, makeSuggestion({ rating: "dislike" })) as never,
  );
  const remove = vi
    .spyOn(api, "DELETE")
    .mockResolvedValue(apiAnswer(200, makeSuggestion()) as never);
  const { Toaster } = await import("@/components/ui/toast");
  renderWithQueries(
    <>
      <Harness initial={makeSuggestion()} />
      <Toaster />
    </>,
  );

  swipe(board(), -150);
  fireEvent.click(await screen.findByRole("button", { name: "Undo" }));

  await waitFor(() => expect(remove).toHaveBeenCalledOnce());
});

it("scrolling, short moves, and a mouse don't rate anything", () => {
  const post = vi.spyOn(api, "POST");
  renderWithQueries(<Harness initial={makeSuggestion()} />);

  swipe(board(), 40, 300);
  swipe(board(), 60);
  swipe(board(), 200, 0, "mouse");

  expect(post).not.toHaveBeenCalled();
});
