import { defineConfig, devices } from "@playwright/test";

// End-to-end tests: real browsers against a running WearWise. Locally, start it first with
// `make dev`; against production, set E2E_BASE_URL. They make their own throwaway accounts
// and delete them afterwards.
export default defineConfig({
  testDir: "e2e",
  // The free server can take a minute to wake.
  timeout: 120_000,
  expect: { timeout: 30_000 },
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:3000",
    trace: "retain-on-failure",
    // Chrome already installed on the machine, if asked for; otherwise Playwright's own.
    channel: process.env.E2E_CHANNEL || undefined,
  },
  projects: [
    { name: "desktop", use: { ...devices["Desktop Chrome"] } },
    { name: "phone", use: { ...devices["Pixel 7"] } },
  ],
});
