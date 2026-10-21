import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { api } from "@/lib/api/client";
import { apiAnswer, renderWithQueries, sentBody } from "@/lib/test-utils";

import { WeeklyEmail } from "./weekly-email";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const OFF = {
  on: false,
  waiting_for_confirmation: false,
  weekday: 6,
  email: "sam@example.com",
  confirmed: false,
  preview_only: false,
};

it("turning it on sends the confirmation link first and says so", async () => {
  vi.spyOn(api, "GET").mockResolvedValue(apiAnswer(200, OFF) as never);
  const post = vi.spyOn(api, "POST").mockResolvedValue(
    apiAnswer(200, {
      ...OFF,
      waiting_for_confirmation: true,
      weekday: 4,
    }) as never,
  );
  renderWithQueries(<WeeklyEmail isDemo={false} />);

  fireEvent.change(await screen.findByLabelText("Day"), {
    target: { value: "4" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Turn it on" }));

  await waitFor(() => expect(post).toHaveBeenCalledOnce());
  expect(post.mock.calls[0]?.[0]).toBe("/api/v1/digest-settings/on");
  expect(sentBody(post)).toEqual({ weekday: 4 });
  expect(await screen.findByText(/A link is on its way to/)).toBeDefined();
  expect(
    screen.getByRole("button", { name: "Send the link again" }),
  ).toBeDefined();
});

it("when on, it says when and to where, and can be turned off", async () => {
  vi.spyOn(api, "GET").mockResolvedValue(
    apiAnswer(200, { ...OFF, on: true, confirmed: true }) as never,
  );
  const post = vi
    .spyOn(api, "POST")
    .mockResolvedValue(apiAnswer(200, { ...OFF, confirmed: true }) as never);
  renderWithQueries(<WeeklyEmail isDemo={false} />);

  expect(await screen.findByText(/On: every Sunday morning, to/)).toBeDefined();
  fireEvent.click(screen.getByRole("button", { name: "Turn it off" }));

  await waitFor(() =>
    expect(post).toHaveBeenCalledWith("/api/v1/digest-settings/off"),
  );
  expect(
    await screen.findByRole("button", { name: "Turn it on" }),
  ).toBeDefined();
});

it("while email is limited to the owner, it says so instead of offering a button", async () => {
  vi.spyOn(api, "GET").mockResolvedValue(
    apiAnswer(200, { ...OFF, preview_only: true }) as never,
  );
  renderWithQueries(<WeeklyEmail isDemo={false} />);

  expect(
    await screen.findByText(/goes only to WearWise's owner/),
  ).toBeDefined();
  expect(screen.queryByRole("button", { name: "Turn it on" })).toBeNull();
});

it("a demo is told it can't get email", () => {
  vi.spyOn(api, "GET").mockResolvedValue(apiAnswer(200, OFF) as never);
  renderWithQueries(<WeeklyEmail isDemo />);

  expect(screen.getByText(/A demo account can't get email/)).toBeDefined();
  expect(screen.queryByRole("button")).toBeNull();
});
