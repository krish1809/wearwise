import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { api } from "@/lib/api/client";
import { apiAnswer, renderWithQueries, typeInto } from "@/lib/test-utils";

import { LoginForm } from "./login-form";

const nav = vi.hoisted(() => ({
  replace: vi.fn(),
  search: new URLSearchParams(),
}));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: nav.replace }),
  useSearchParams: () => nav.search,
}));

beforeEach(() => {
  nav.search = new URLSearchParams();
  // The form wakes the backend on load; don't let that reach the network.
  vi.spyOn(api, "GET").mockResolvedValue(apiAnswer(200) as never);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  nav.replace.mockReset();
});

function submit() {
  fireEvent.click(screen.getByRole("button", { name: "Log in" }));
}

it("asks for both fields before sending anything", async () => {
  const post = vi.spyOn(api, "POST");
  renderWithQueries(<LoginForm />);

  submit();

  expect(await screen.findByText("Enter your email address.")).toBeDefined();
  expect(screen.getByText("Enter your password.")).toBeDefined();
  expect(post).not.toHaveBeenCalled();
});

it("shows the API's message when the details don't match", async () => {
  const message =
    "That email and password don't match an account. Check them and try again.";
  vi.spyOn(api, "POST").mockResolvedValue(
    apiAnswer(401, {
      error: { code: "invalid_credentials", message },
    }) as never,
  );
  renderWithQueries(<LoginForm />);

  typeInto("Email", "sam@example.com");
  typeInto("Password", "not the password");
  submit();

  expect(await screen.findByText(message)).toBeDefined();
  expect(nav.replace).not.toHaveBeenCalled();
});

function logInAs(onboardingCompleted: boolean) {
  const user = {
    id: "1",
    email: "sam@example.com",
    name: "Sam Lee",
    onboarding_completed: onboardingCompleted,
  };
  vi.spyOn(api, "POST").mockResolvedValue(apiAnswer(200, user) as never);
  const cache = renderWithQueries(<LoginForm />);
  typeInto("Email", "sam@example.com");
  typeInto("Password", "correct horse battery staple");
  submit();
  return { user, cache };
}

it("goes back to the page the person was heading for", async () => {
  nav.search = new URLSearchParams("next=/settings");

  const { user, cache } = logInAs(true);

  await waitFor(() => expect(nav.replace).toHaveBeenCalledWith("/settings"));
  expect(cache.getQueryData(["me"])).toEqual(user);
});

it("goes home once onboarding is done", async () => {
  logInAs(true);

  await waitFor(() => expect(nav.replace).toHaveBeenCalledWith("/home"));
});

it("picks up onboarding until it is finished or skipped", async () => {
  logInAs(false);

  await waitFor(() => expect(nav.replace).toHaveBeenCalledWith("/onboarding"));
});

it("says so when a session has ended", () => {
  nav.search = new URLSearchParams("reason=expired");

  renderWithQueries(<LoginForm />);

  expect(
    screen.getByText("Your session has ended. Log in again."),
  ).toBeDefined();
});
