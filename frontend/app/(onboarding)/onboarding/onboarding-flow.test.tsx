import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import {
  echoProfilePatch,
  makeProfile,
  REFERENCE,
} from "@/components/profile/test-data";
import { api } from "@/lib/api/client";
import type { Profile } from "@/lib/profile";
import { apiAnswer, renderWithQueries } from "@/lib/test-utils";

import { OnboardingFlow } from "./onboarding-flow";

const nav = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: nav.replace }),
}));

const USER = {
  id: "1",
  email: "sam@example.com",
  name: null,
  onboarding_completed: false,
};

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  nav.replace.mockReset();
});

function start(profile: Profile = makeProfile()) {
  vi.spyOn(api, "GET").mockImplementation(async (path) => {
    if (path === "/api/v1/profile") return apiAnswer(200, profile) as never;
    if (path === "/api/v1/reference") return apiAnswer(200, REFERENCE) as never;
    return apiAnswer(200, USER) as never;
  });
  const patch = vi
    .spyOn(api, "PATCH")
    .mockImplementation(echoProfilePatch(profile));
  const post = vi.spyOn(api, "POST").mockResolvedValue(apiAnswer(204) as never);
  renderWithQueries(<OnboardingFlow />);
  return { patch, post };
}

const click = (name: string) =>
  fireEvent.click(screen.getByRole("button", { name }));

it("skips everything and goes home", async () => {
  const { post, patch } = start();

  await screen.findByText("Step 1 of 6");
  click("Skip all");

  await waitFor(() => expect(nav.replace).toHaveBeenCalledWith("/home"));
  expect(post).toHaveBeenCalledWith("/api/v1/onboarding/finish", {
    body: { skipped: true },
  });
  expect(patch).not.toHaveBeenCalled();
});

it("saves a step with Continue, moves on with Skip, and goes back with Back", async () => {
  const { patch } = start();

  await screen.findByText("Step 1 of 6");
  fireEvent.click(screen.getByRole("button", { name: "Menswear" }));
  click("Continue");

  expect(await screen.findByText("Step 2 of 6")).toBeDefined();
  expect(patch).toHaveBeenLastCalledWith("/api/v1/profile", {
    body: { sections: ["menswear"], city: null, onboarding_step: 1 },
  });

  click("Skip this step");
  expect(await screen.findByText("Step 3 of 6")).toBeDefined();
  expect(patch).toHaveBeenLastCalledWith("/api/v1/profile", {
    body: { onboarding_step: 2 },
  });

  click("Back");
  expect(await screen.findByText("Step 2 of 6")).toBeDefined();
  expect(screen.getByRole("heading", { name: "Sizes and fit" })).toBe(
    document.activeElement,
  );
});

it("picks up at the step reached last time", async () => {
  start(makeProfile({ onboarding_step: 3 }));

  expect(await screen.findByText("Step 4 of 6")).toBeDefined();
  expect(screen.getByRole("heading", { name: "Occasions" })).toBeDefined();
});

it("finishes after the last step", async () => {
  const { post } = start(makeProfile({ onboarding_step: 5 }));

  await screen.findByText("Step 6 of 6");
  click("Finish");

  await waitFor(() => expect(nav.replace).toHaveBeenCalledWith("/home"));
  expect(post).toHaveBeenCalledWith("/api/v1/onboarding/finish", {
    body: { skipped: false },
  });
});
