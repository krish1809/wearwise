import {
  cleanup,
  fireEvent,
  screen,
  waitFor,
  within,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { api } from "@/lib/api/client";
import { apiAnswer, renderWithQueries } from "@/lib/test-utils";

import { DeleteAccountDialog } from "./delete-account-dialog";

const nav = vi.hoisted(() => ({ replace: vi.fn() }));
vi.mock("next/navigation", () => ({
  useRouter: () => ({ replace: nav.replace }),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  nav.replace.mockReset();
});

async function openDialog() {
  renderWithQueries(<DeleteAccountDialog email="sam@example.com" />);
  fireEvent.click(screen.getByRole("button", { name: "Delete account" }));
  const dialog = await screen.findByRole("dialog");
  return {
    dialog,
    confirm: within(dialog).getByRole("button", { name: "Delete account" }),
    type: (value: string) =>
      fireEvent.change(
        within(dialog).getByLabelText("Type sam@example.com to confirm"),
        { target: { value } },
      ),
  };
}

it("keeps Delete disabled until the email is typed", async () => {
  const { confirm, type } = await openDialog();

  expect(confirm).toHaveProperty("disabled", true);
  type("sam@exam");
  expect(confirm).toHaveProperty("disabled", true);
  type(" SAM@example.com ");
  expect(confirm).toHaveProperty("disabled", false);
});

it("deletes the account and goes to the front page", async () => {
  const post = vi.spyOn(api, "POST").mockResolvedValue(apiAnswer(204) as never);
  const { confirm, type } = await openDialog();

  type("sam@example.com");
  fireEvent.click(confirm);

  await waitFor(() => expect(nav.replace).toHaveBeenCalledWith("/"));
  expect(post).toHaveBeenCalledWith("/api/v1/account/delete", {
    body: { confirm_email: "sam@example.com" },
  });
});
