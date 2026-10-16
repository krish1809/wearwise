import {
  cleanup,
  fireEvent,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { REFERENCE } from "@/components/profile/test-data";
import { CATEGORIES, makeItem } from "@/components/wardrobe/test-data";
import { api } from "@/lib/api/client";
import { apiAnswer, renderWithQueries } from "@/lib/test-utils";
import type { ItemSummary } from "@/lib/wardrobe";

import { WardrobeContent } from "./wardrobe-content";

const nav = vi.hoisted(() => ({
  replace: vi.fn(),
  search: new URLSearchParams(),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: nav.replace }),
  usePathname: () => "/wardrobe",
  useSearchParams: () => nav.search,
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  nav.replace.mockReset();
  nav.search = new URLSearchParams();
});

function showWardrobe(items: ItemSummary[]) {
  const get = vi.spyOn(api, "GET").mockImplementation(async (path) => {
    if (path === "/api/v1/reference") return apiAnswer(200, REFERENCE) as never;
    if (path === "/api/v1/categories")
      return apiAnswer(200, CATEGORIES) as never;
    return apiAnswer(200, {
      items,
      next_cursor: null,
      total: items.length,
    }) as never;
  });
  renderWithQueries(<WardrobeContent />);
  return get;
}

it("shows each item with its name, colour, and category", async () => {
  showWardrobe([
    makeItem(),
    makeItem({
      id: "item-2",
      display_name: "Weekend sneakers",
      category_id: "sneakers",
      status: "laundry",
    }),
  ]);

  expect(await screen.findByText("2 items")).toBeDefined();
  expect(
    screen.getByRole("link", { name: /Navy t-shirt/ }).getAttribute("href"),
  ).toBe("/wardrobe/item-1");
  expect(screen.getByText("In the laundry · Navy · Sneakers")).toBeDefined();
  expect(
    screen.getByRole("img", { name: "Navy t-shirt, Navy · T-shirt, no photo" }),
  ).toBeDefined();
});

it("puts a chosen filter in the address bar", async () => {
  showWardrobe([makeItem()]);
  const rail = await screen.findByRole("complementary", { name: "Filters" });

  fireEvent.click(within(rail).getByRole("button", { name: "Navy" }));

  expect(nav.replace).toHaveBeenCalledWith("/wardrobe?color=navy", {
    scroll: false,
  });
});

it("reads filters from the address bar and offers to clear them", async () => {
  nav.search = new URLSearchParams("color=navy&season=summer");
  const get = showWardrobe([]);

  expect(await screen.findByText("Nothing matches")).toBeDefined();
  expect(get).toHaveBeenCalledWith(
    "/api/v1/items",
    expect.objectContaining({
      params: {
        query: expect.objectContaining({ color: ["navy"], season: ["summer"] }),
      },
    }),
  );
  fireEvent.click(screen.getByRole("button", { name: "Remove Navy" }));
  expect(nav.replace).toHaveBeenCalledWith("/wardrobe?season=summer", {
    scroll: false,
  });
});

it("explains what to do when the wardrobe is empty", async () => {
  showWardrobe([]);

  expect(await screen.findByText("Your wardrobe is empty")).toBeDefined();
  expect(
    screen
      .getByRole("link", { name: "Add your first item" })
      .getAttribute("href"),
  ).toBe("/wardrobe/new");
});

it("searches once the person pauses typing", async () => {
  showWardrobe([makeItem()]);
  await screen.findByText("1 item");

  fireEvent.change(screen.getByLabelText("Search your wardrobe"), {
    target: { value: "navy" },
  });

  expect(nav.replace).not.toHaveBeenCalled();
  await waitFor(() =>
    expect(nav.replace).toHaveBeenCalledWith("/wardrobe?q=navy", {
      scroll: false,
    }),
  );
});
