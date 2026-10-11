import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { HealthStatus } from "@/components/health-status";
import { waitForHealth } from "@/lib/health";

vi.mock("@/lib/health", () => ({ waitForHealth: vi.fn() }));
const mockedWaitForHealth = vi.mocked(waitForHealth);

afterEach(() => {
  cleanup();
  vi.resetAllMocks();
});

it("says the API and database are ok", async () => {
  mockedWaitForHealth.mockResolvedValue({ kind: "ok", version: "0.0.1" });

  render(<HealthStatus />);

  expect(await screen.findByText("API ok, database ok")).toBeDefined();
  expect(screen.getByText("API version 0.0.1")).toBeDefined();
});

it("says the database is unreachable, and checks again when asked", async () => {
  mockedWaitForHealth
    .mockResolvedValueOnce({ kind: "database-down", version: "0.0.1" })
    .mockResolvedValueOnce({ kind: "ok", version: "0.0.1" });

  render(<HealthStatus />);
  expect(await screen.findByText("API ok, database unreachable")).toBeDefined();
  fireEvent.click(screen.getByRole("button", { name: "Try again" }));

  expect(await screen.findByText("API ok, database ok")).toBeDefined();
  expect(mockedWaitForHealth).toHaveBeenCalledTimes(2);
});

it("says when the API can't be reached", async () => {
  mockedWaitForHealth.mockResolvedValue({ kind: "api-down" });

  render(<HealthStatus />);

  expect(await screen.findByText("Can't reach the API.")).toBeDefined();
  expect(screen.getByRole("button", { name: "Try again" })).toBeDefined();
});
