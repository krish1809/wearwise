import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { makeProfile, REFERENCE } from "@/components/profile/test-data";
import { brief } from "@/components/shopping/test-data";
import { api } from "@/lib/api/client";
import type { ChatMessage, ThreadDetail } from "@/lib/stylist";
import { apiAnswer, renderWithQueries, sentBody } from "@/lib/test-utils";

import { StylistContent } from "./stylist-content";

const nav = vi.hoisted(() => {
  const state = {
    search: new URLSearchParams(),
    // Like the router: the address changes, and the page reads it again.
    replace: vi.fn((url: string) => {
      state.search = new URLSearchParams(url.split("?")[1] ?? "");
    }),
  };
  return state;
});
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: nav.replace, push: vi.fn() }),
  usePathname: () => "/stylist",
  useSearchParams: () => nav.search,
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  nav.replace.mockClear();
  nav.search = new URLSearchParams();
});

const SHIRT = brief("shirt", "White shirt");

function answer(): ChatMessage[] {
  return [
    {
      id: "m1",
      role: "user",
      text: "What should I wear to college tomorrow?",
      cards: [],
      created_at: "2026-10-20T10:00:00Z",
    },
    {
      id: "m2",
      role: "assistant",
      text: "Your white shirt is a safe start.",
      cards: [
        {
          type: "item",
          items: [SHIRT],
          removed: false,
          candidate: null,
          staple: null,
          action: null,
        },
        {
          type: "action",
          items: [],
          removed: false,
          candidate: null,
          staple: null,
          action: {
            id: "a1",
            kind: "save_outfit",
            status: "pending",
            summary: "Save outfit: White shirt",
            items: [SHIRT],
            result: {},
          },
        },
      ],
      created_at: "2026-10-20T10:00:01Z",
    },
  ];
}

function show(
  status: { available: boolean; reason: string | null },
  thread?: () => ThreadDetail,
) {
  vi.spyOn(api, "GET").mockImplementation(async (path) => {
    if (path === "/api/v1/ai/status") return apiAnswer(200, status) as never;
    if (path === "/api/v1/chat/threads") return apiAnswer(200, []) as never;
    if (path === "/api/v1/chat/threads/{thread_id}" && thread)
      return apiAnswer(200, thread()) as never;
    if (path === "/api/v1/reference") return apiAnswer(200, REFERENCE) as never;
    if (path === "/api/v1/profile")
      return apiAnswer(200, makeProfile()) as never;
    if (path === "/api/v1/categories") return apiAnswer(200, []) as never;
    return apiAnswer(404, {}) as never;
  });
  renderWithQueries(<StylistContent />);
}

it("says plainly when the stylist is switched off", async () => {
  show({ available: false, reason: "off" });

  expect(await screen.findByText("The stylist is resting")).toBeDefined();
  expect(screen.getByText(/isn't switched on/)).toBeDefined();
  expect(screen.queryByLabelText("Message")).toBeNull();
});

it("asks, shows the answer with its cards, and confirms a proposal", async () => {
  show({ available: true, reason: null });
  const post = vi.spyOn(api, "POST").mockImplementation(async (path) => {
    if (path === "/api/v1/chat/messages")
      return apiAnswer(200, {
        thread: {
          id: "t1",
          title: "College",
          updated_at: "2026-10-20T10:00:01Z",
        },
        messages: answer(),
      }) as never;
    return apiAnswer(200, {
      id: "a1",
      kind: "save_outfit",
      status: "done",
      summary: "Save outfit: White shirt",
      items: [SHIRT],
      result: { outfit_id: "o1" },
    }) as never;
  });

  fireEvent.click(
    await screen.findByRole("button", {
      name: "What should I wear to college tomorrow?",
    }),
  );

  expect(
    await screen.findByText("Your white shirt is a safe start."),
  ).toBeDefined();
  expect(sentBody(post)).toEqual({
    thread_id: null,
    text: "What should I wear to college tomorrow?",
  });
  expect(
    screen.getByRole("link", { name: "White shirt" }).getAttribute("href"),
  ).toBe("/wardrobe/shirt");
  expect(nav.replace).toHaveBeenCalledWith("/stylist?thread=t1");

  fireEvent.click(screen.getByRole("button", { name: "Confirm" }));

  expect(
    await screen.findByRole("link", { name: "See the outfit" }),
  ).toBeDefined();
  expect(post.mock.calls[1]?.[0]).toBe(
    "/api/v1/chat/actions/{action_id}/confirm",
  );
});

it("keeps the question when the stylist can't answer", async () => {
  show({ available: true, reason: null });
  vi.spyOn(api, "POST").mockResolvedValue(
    apiAnswer(503, {
      error: {
        code: "ai_down",
        message:
          "The stylist didn't respond. Try again in a minute; everything else works as usual.",
      },
    }) as never,
  );

  const box = await screen.findByLabelText("Message");
  fireEvent.change(box, { target: { value: "Something for a wedding?" } });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));

  expect(await screen.findByText(/didn't respond/)).toBeDefined();
  expect((screen.getByLabelText("Message") as HTMLTextAreaElement).value).toBe(
    "Something for a wedding?",
  );
});

it("shows a proposal still waiting as not done once another message is sent", async () => {
  const thread = {
    id: "t1",
    title: "College",
    updated_at: "2026-10-20T10:00:01Z",
  };
  const later: ChatMessage[] = [
    {
      id: "m3",
      role: "user",
      text: "Something warmer?",
      cards: [],
      created_at: "2026-10-20T10:01:00Z",
    },
    {
      id: "m4",
      role: "assistant",
      text: "Then a jacket over the shirt.",
      cards: [],
      created_at: "2026-10-20T10:01:01Z",
    },
  ];
  let sent = 0;
  // What the server holds: the new message answered the waiting proposal with "not now".
  const held = (): ThreadDetail => {
    const [asked, answered] = answer();
    if (sent < 2 || !asked || !answered)
      return { ...thread, messages: answer() };
    const cards = answered.cards.map((card) =>
      card.action
        ? { ...card, action: { ...card.action, status: "cancelled" } }
        : card,
    );
    return { ...thread, messages: [asked, { ...answered, cards }, ...later] };
  };
  show({ available: true, reason: null }, held);
  vi.spyOn(api, "POST").mockImplementation(async () => {
    sent += 1;
    return apiAnswer(200, {
      thread,
      messages: sent === 1 ? answer() : later,
    }) as never;
  });
  fireEvent.click(
    await screen.findByRole("button", {
      name: "What should I wear to college tomorrow?",
    }),
  );
  expect(await screen.findByRole("button", { name: "Confirm" })).toBeDefined();

  fireEvent.change(screen.getByLabelText("Message"), {
    target: { value: "Something warmer?" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Send" }));

  expect(
    await screen.findByText("Then a jacket over the shirt."),
  ).toBeDefined();
  expect(await screen.findByText("Not done.")).toBeDefined();
  expect(screen.queryByRole("button", { name: "Confirm" })).toBeNull();
});
