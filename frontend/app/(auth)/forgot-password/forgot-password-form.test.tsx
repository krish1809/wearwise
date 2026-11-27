import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { api } from "@/lib/api/client";
import { apiAnswer, sentBody } from "@/lib/test-utils";

import { ForgotPasswordForm } from "./forgot-password-form";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

it("says the same thing whether or not there's an account", async () => {
  const post = vi.spyOn(api, "POST").mockResolvedValue(apiAnswer(204) as never);
  render(<ForgotPasswordForm />);

  fireEvent.change(screen.getByLabelText("Email"), {
    target: { value: "sam@example.com" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Send the link" }));

  await waitFor(() => expect(post).toHaveBeenCalledOnce());
  expect(sentBody(post)).toEqual({ email: "sam@example.com" });
  expect(
    await screen.findByText(/If there's an account for that address/),
  ).toBeDefined();
});
