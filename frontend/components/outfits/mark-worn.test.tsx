import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { api } from "@/lib/api/client";
import { todayIso } from "@/lib/dates";
import { apiAnswer, renderWithQueries } from "@/lib/test-utils";

import { MarkWorn } from "./mark-worn";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("logs today's date from the browser's own calendar in one tap", async () => {
  const post = vi
    .spyOn(api, "POST")
    .mockResolvedValue(apiAnswer(201, {}) as never);
  renderWithQueries(<MarkWorn what={{ outfit_id: "outfit-1" }} />);

  fireEvent.click(screen.getByRole("button", { name: "I wore this today" }));

  await waitFor(() =>
    expect(post).toHaveBeenCalledWith("/api/v1/wear-logs", {
      body: { worn_on: todayIso(), outfit_id: "outfit-1" },
    }),
  );
});

it("says when it's already worn today instead of offering a second tap", () => {
  renderWithQueries(<MarkWorn what={{ item_ids: ["shirt"] }} wornToday />);

  const button = screen.getByRole("button", { name: "Worn today" });
  expect(button).toHaveProperty("disabled", true);
  expect(screen.getByRole("button", { name: "Another day" })).toBeDefined();
});

it("logs another day from the dialog", async () => {
  const post = vi
    .spyOn(api, "POST")
    .mockResolvedValue(apiAnswer(201, {}) as never);
  renderWithQueries(<MarkWorn what={{ item_ids: ["shirt", "chinos"] }} />);

  fireEvent.click(screen.getByRole("button", { name: "Another day" }));
  fireEvent.change(await screen.findByLabelText("Day"), {
    target: { value: "2026-10-01" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Mark as worn" }));

  await waitFor(() =>
    expect(post).toHaveBeenCalledWith("/api/v1/wear-logs", {
      body: { worn_on: "2026-10-01", item_ids: ["shirt", "chinos"] },
    }),
  );
});
