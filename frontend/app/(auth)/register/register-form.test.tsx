import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { api } from "@/lib/api/client";
import { apiAnswer, renderWithQueries, typeInto } from "@/lib/test-utils";

import { RegisterForm } from "./register-form";

const nav = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: nav.replace }),
}));

beforeEach(() => {
  vi.spyOn(api, "GET").mockResolvedValue(apiAnswer(200) as never);
});

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  nav.replace.mockReset();
});

function submit() {
  fireEvent.click(screen.getByRole("button", { name: "Create account" }));
}

it("checks the password length before sending", async () => {
  const post = vi.spyOn(api, "POST");
  renderWithQueries(<RegisterForm />);

  typeInto("Email", "sam@example.com");
  typeInto("Password", "short");
  submit();

  expect(await screen.findByText("Use at least 12 characters.")).toBeDefined();
  expect(post).not.toHaveBeenCalled();
});

it("puts a taken email's message under the email field", async () => {
  const message = "An account with this email already exists. Log in instead.";
  vi.spyOn(api, "POST").mockResolvedValue(
    apiAnswer(409, {
      error: { code: "email_taken", message, fields: { email: message } },
    }) as never,
  );
  renderWithQueries(<RegisterForm />);

  typeInto("Email", "sam@example.com");
  typeInto("Password", "correct horse battery staple");
  submit();

  const email = screen.getByLabelText("Email");
  await waitFor(() => expect(email.getAttribute("aria-invalid")).toBe("true"));
  expect(screen.getByText(message)).toBeDefined();
});

it("logs the new person in and starts onboarding, sending no name when none was given", async () => {
  const user = {
    id: "1",
    email: "sam@example.com",
    name: null,
    onboarding_completed: false,
  };
  const post = vi
    .spyOn(api, "POST")
    .mockResolvedValue(apiAnswer(201, user) as never);
  renderWithQueries(<RegisterForm />);

  typeInto("Email", "sam@example.com");
  typeInto("Password", "correct horse battery staple");
  submit();

  await waitFor(() => expect(nav.replace).toHaveBeenCalledWith("/onboarding"));
  expect(post).toHaveBeenCalledWith("/api/v1/auth/register", {
    body: {
      name: null,
      email: "sam@example.com",
      password: "correct horse battery staple",
    },
  });
});
