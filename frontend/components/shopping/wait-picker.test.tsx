import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { Toaster } from "@/components/ui/toast";
import { api } from "@/lib/api/client";
import { isoDay } from "@/lib/dates";
import { apiAnswer, renderWithQueries, sentBody } from "@/lib/test-utils";

import { makeCandidate } from "./test-data";
import { WaitPicker } from "./wait-picker";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("sleeping on it sets the day to ask again, in the person's own calendar", async () => {
  const patch = vi
    .spyOn(api, "PATCH")
    .mockResolvedValue(apiAnswer(200, makeCandidate()) as never);
  renderWithQueries(<WaitPicker candidate={makeCandidate()} />);

  fireEvent.click(screen.getByRole("button", { name: "2 weeks" }));

  const day = new Date();
  day.setDate(day.getDate() + 14);
  await waitFor(() =>
    expect(sentBody(patch)).toEqual({ remind_on: isoDay(day) }),
  );
});

it("on the day, asks whether it's still wanted; skipping can be undone", async () => {
  const due = makeCandidate({ remind_on: "2026-10-20", reminder_due: true });
  const patch = vi
    .spyOn(api, "PATCH")
    .mockResolvedValue(apiAnswer(200, due) as never);
  renderWithQueries(
    <>
      <WaitPicker candidate={due} />
      <Toaster />
    </>,
  );

  expect(screen.getByText(/Still want it\?/)).toBeDefined();
  fireEvent.click(screen.getByRole("button", { name: "Skip it" }));
  fireEvent.click(await screen.findByRole("button", { name: "Undo" }));

  await waitFor(() => expect(patch).toHaveBeenCalledTimes(2));
  expect(sentBody(patch, 0)).toEqual({ status: "skipped" });
  expect(sentBody(patch, 1)).toEqual({ status: "considering" });
});

it("keeping it clears the reminder", async () => {
  const due = makeCandidate({ remind_on: "2026-10-20", reminder_due: true });
  const patch = vi
    .spyOn(api, "PATCH")
    .mockResolvedValue(apiAnswer(200, due) as never);
  renderWithQueries(<WaitPicker candidate={due} />);

  fireEvent.click(screen.getByRole("button", { name: "Yes, keep it" }));

  await waitFor(() => expect(sentBody(patch)).toEqual({ remind_on: null }));
});
