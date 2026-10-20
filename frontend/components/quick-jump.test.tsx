import { cleanup, fireEvent, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { brief } from "@/components/shopping/test-data";
import { api } from "@/lib/api/client";
import { apiAnswer, renderWithQueries } from "@/lib/test-utils";

import { QuickJump } from "./quick-jump";

const nav = vi.hoisted(() => ({ push: vi.fn() }));
vi.mock("next/navigation", () => ({ useRouter: () => nav }));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  nav.push.mockReset();
});

function show() {
  vi.spyOn(api, "GET").mockImplementation(async (path) => {
    if (path === "/api/v1/ai/status")
      return apiAnswer(200, { available: false, reason: "off" }) as never;
    if (path === "/api/v1/items")
      return apiAnswer(200, {
        items: [{ ...brief("i1", "Navy linen shirt") }],
        next_cursor: null,
        total: 1,
      }) as never;
    return apiAnswer(404, {}) as never;
  });
  renderWithQueries(<QuickJump />);
}

it("opens with Ctrl+K, narrows as you type, and Enter goes there", async () => {
  show();

  fireEvent.keyDown(window, { key: "k", ctrlKey: true });
  const box = await screen.findByRole("combobox", {
    name: "Find a page, action, or item",
  });
  fireEvent.change(box, { target: { value: "laun" } });

  const options = screen.getAllByRole("option");
  expect(options.map((o) => o.textContent)).toEqual(["LaundryGo to"]);
  expect(options[0]?.getAttribute("aria-selected")).toBe("true");
  fireEvent.keyDown(box, { key: "Enter" });

  expect(nav.push).toHaveBeenCalledWith("/laundry");
});

it("moves with the arrow keys", async () => {
  show();

  fireEvent.click(screen.getByRole("button", { name: /Jump to/ }));
  const box = await screen.findByRole("combobox");
  fireEvent.change(box, { target: { value: "plan" } });

  const options = screen.getAllByRole("option");
  expect(options.map((o) => o.textContent)).toEqual([
    "My WeekGo to",
    "Plan a starter wardrobeDo",
  ]);
  fireEvent.keyDown(box, { key: "ArrowDown" });
  expect(options[1]?.getAttribute("aria-selected")).toBe("true");
  fireEvent.keyDown(box, { key: "ArrowDown" });
  expect(options[0]?.getAttribute("aria-selected")).toBe("true");
  fireEvent.keyDown(box, { key: "ArrowUp" });
  fireEvent.keyDown(box, { key: "Enter" });

  expect(nav.push).toHaveBeenCalledWith("/shopping/plan");
});

it("finds your items by name", async () => {
  show();

  fireEvent.click(screen.getByRole("button", { name: /Jump to/ }));
  const box = await screen.findByRole("combobox");
  fireEvent.change(box, { target: { value: "linen" } });

  fireEvent.click(
    await screen.findByRole("option", { name: /Navy linen shirt/ }),
  );

  expect(nav.push).toHaveBeenCalledWith("/wardrobe/i1");
});

it("leaves out the stylist while it's switched off", async () => {
  show();

  fireEvent.keyDown(window, { key: "k", metaKey: true });
  const box = await screen.findByRole("combobox");
  fireEvent.change(box, { target: { value: "stylist" } });

  expect(await screen.findByText("Nothing matches.")).toBeDefined();
});
