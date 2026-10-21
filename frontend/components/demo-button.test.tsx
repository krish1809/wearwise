import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { api } from "@/lib/api/client";
import { meQueryKey } from "@/lib/auth";
import { apiAnswer, renderWithQueries, sentBody } from "@/lib/test-utils";

import { DemoButton } from "./demo-button";

const push = vi.fn();
vi.mock("next/navigation", () => ({ useRouter: () => ({ push }) }));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  push.mockReset();
});

const VISITOR = {
  id: "u1",
  email: "visitor-1a2b3c4d5e6f7a8b@demo.wearwise.invalid",
  name: null,
  onboarding_completed: true,
  is_demo: true,
  created_at: "2026-10-21T08:00:00Z",
  demo_ends_at: "2026-10-22T08:00:00Z",
};

it("starts a demo with the chosen wardrobe and goes straight in", async () => {
  const post = vi
    .spyOn(api, "POST")
    .mockResolvedValue(apiAnswer(201, VISITOR) as never);
  const cache = renderWithQueries(<DemoButton />);

  fireEvent.pointerDown(screen.getByRole("button", { name: "Try the demo" }), {
    button: 0,
    ctrlKey: false,
  });
  fireEvent.click(
    await screen.findByRole("menuitem", { name: "A womenswear wardrobe" }),
  );

  await waitFor(() => expect(push).toHaveBeenCalledWith("/home"));
  expect(sentBody(post)).toEqual({ section: "womenswear" });
  expect(cache.getQueryData(meQueryKey)).toEqual(VISITOR);
});
