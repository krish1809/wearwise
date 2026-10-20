import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { api } from "@/lib/api/client";
import type { ShopFor } from "@/lib/shopping";
import { apiAnswer, renderWithQueries } from "@/lib/test-utils";

import { ShopPanel } from "./shop-panel";

vi.mock("next/navigation", () => ({ useRouter: () => ({ push: vi.fn() }) }));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const SHOP: ShopFor = {
  query: "Navy chinos men",
  links: [
    {
      shop_id: "myntra",
      shop: "Myntra",
      url: "https://www.myntra.com/navy-chinos-men?rawQuery=Navy%20chinos%20men",
    },
    {
      shop_id: "amazon",
      shop: "Amazon",
      url: "https://www.amazon.in/s?k=Navy+chinos+men",
    },
  ],
  price_cap: 200000,
  group_name: "Bottoms",
  products: [
    {
      id: "p1",
      title: "Arrow Men Navy Chinos",
      brand: null,
      url: null,
      image_url: null,
      price: null,
      category_id: "chinos",
      color_primary: "navy",
      hex: "#1F2A44",
      is_demo: true,
      source: "fashion-product-images",
      fetched_at: "2026-10-20T10:00:00Z",
      coverage_gain: 2.1,
      new_outfits: 3,
      redundancy: 0.2,
      closest: null,
    },
  ],
};

it("links to each shop's search, with the usual spend and demo products marked", async () => {
  const get = vi
    .spyOn(api, "GET")
    .mockResolvedValue(apiAnswer(200, SHOP) as never);
  renderWithQueries(
    <ShopPanel
      target={{ archetypeId: "navy_chinos" }}
      name="Navy chinos"
      trigger={<button type="button">Find it</button>}
    />,
  );

  // Nothing is asked for until the panel opens.
  expect(get).not.toHaveBeenCalled();
  fireEvent.click(screen.getByRole("button", { name: "Find it" }));

  const myntra = await screen.findByRole("link", { name: /Myntra/ });
  expect(myntra.getAttribute("href")).toBe(SHOP.links[0]?.url);
  expect(myntra.getAttribute("rel")).toBe("noopener noreferrer nofollow");
  expect(
    screen.getByText("Look for under ₹2,000: your usual spend on bottoms."),
  ).toBeDefined();
  expect(screen.getByText("Demo")).toBeDefined();
  expect(
    screen.getByText("3 new good outfits where you're short"),
  ).toBeDefined();
});
