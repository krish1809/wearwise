import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { makeProfile, REFERENCE } from "@/components/profile/test-data";
import { makeCandidate } from "@/components/shopping/test-data";
import { CATEGORIES } from "@/components/wardrobe/test-data";
import { api } from "@/lib/api/client";
import type { LinkPreview } from "@/lib/shopping";
import {
  apiAnswer,
  renderWithQueries,
  sentBody,
  typeInto,
} from "@/lib/test-utils";

import { NewCandidateContent } from "./new-candidate-content";

const nav = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => nav }));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  nav.push.mockReset();
});

const LINK = "https://shop.example.com/p/123";

function preview(overrides: Partial<LinkPreview> = {}): LinkPreview {
  return {
    outcome: "ok",
    url: LINK,
    fetched_at: "2026-10-20T10:00:00Z",
    site: "Example Shop",
    title: "Men Navy Slim Fit Chinos",
    brand: "Northline",
    image_url: "https://cdn.example.com/navy.jpg",
    price: 179900,
    other_currency: null,
    category_id: CATEGORIES[0]?.id ?? null,
    color_primary: "navy",
    fabric: null,
    ...overrides,
  };
}

function show(answer: LinkPreview) {
  vi.spyOn(api, "GET").mockImplementation(async (path) => {
    if (path === "/api/v1/reference") return apiAnswer(200, REFERENCE) as never;
    if (path === "/api/v1/profile")
      return apiAnswer(200, makeProfile()) as never;
    if (path === "/api/v1/categories")
      return apiAnswer(200, CATEGORIES) as never;
    return apiAnswer(404, {}) as never;
  });
  const post = vi.spyOn(api, "POST").mockImplementation(async (path) => {
    if (path === "/api/v1/links/preview")
      return apiAnswer(200, answer) as never;
    return apiAnswer(201, makeCandidate({ id: "c9" })) as never;
  });
  renderWithQueries(<NewCandidateContent />);
  return post;
}

it("a pasted link fills the form, to be checked, and saves as from a link", async () => {
  const post = show(preview());

  typeInto("Product link", LINK);
  fireEvent.click(screen.getByRole("button", { name: "Read the page" }));

  expect(await screen.findByText(/Read from Example Shop/)).toBeDefined();
  expect(
    (screen.getByLabelText("Name (optional)") as HTMLInputElement).value,
  ).toBe("Men Navy Slim Fit Chinos");
  expect(
    (screen.getByLabelText("Price, in rupees (optional)") as HTMLInputElement)
      .value,
  ).toBe("1799");
  expect(screen.getByAltText("Men Navy Slim Fit Chinos")).toBeDefined();

  fireEvent.click(screen.getByRole("button", { name: "Add to shopping list" }));

  await vi.waitFor(() => expect(nav.push).toHaveBeenCalledWith("/shopping/c9"));
  expect(sentBody(post, 1)).toMatchObject({
    source: "link",
    url: LINK,
    image_url: "https://cdn.example.com/navy.jpg",
    price: 179900,
    color_primary: "navy",
  });
});

it("a page the shop won't let us read keeps the link and says why", async () => {
  show(
    preview({
      outcome: "blocked",
      title: null,
      price: null,
      image_url: null,
      site: "Example Shop",
    }),
  );

  typeInto("Product link", LINK);
  fireEvent.click(screen.getByRole("button", { name: "Read the page" }));

  expect(
    await screen.findByText(
      /doesn't allow apps like WearWise to read its pages/,
    ),
  ).toBeDefined();
  expect(
    (screen.getByLabelText("Link (optional)") as HTMLInputElement).value,
  ).toBe(LINK);
  expect(
    (screen.getByLabelText("Name (optional)") as HTMLInputElement).value,
  ).toBe("");
});

it("a link that couldn't be read is saved as typed in, not as read", async () => {
  const post = show(preview({ outcome: "unavailable", title: null }));

  typeInto("Product link", LINK);
  fireEvent.click(screen.getByRole("button", { name: "Read the page" }));
  await screen.findByText(/Couldn't read that page/);
  fireEvent.click(screen.getByRole("button", { name: /Navy/ }));
  fireEvent.change(screen.getByLabelText("Category"), {
    target: { value: CATEGORIES[0]?.id },
  });
  fireEvent.click(screen.getByRole("button", { name: "Add to shopping list" }));

  await vi.waitFor(() => expect(nav.push).toHaveBeenCalled());
  expect(sentBody(post, 1)).toMatchObject({ source: "manual", url: LINK });
});
