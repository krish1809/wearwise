import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { EmailLinkPage } from "./email-link-page";

let search = "token=abc";

vi.mock("next/navigation", () => ({
  useSearchParams: () => new URLSearchParams(search),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
  search = "token=abc";
});

it("waits for a click, so a mail app checking the link can't act for the person", async () => {
  const act = vi.fn().mockResolvedValue({ ok: true });
  render(
    <EmailLinkPage
      button="Stop the weekly email"
      act={act}
      done={<p>Done</p>}
      failed={<p>Failed</p>}
    />,
  );

  expect(act).not.toHaveBeenCalled();
  fireEvent.click(
    screen.getByRole("button", { name: "Stop the weekly email" }),
  );

  await waitFor(() => expect(act).toHaveBeenCalledWith("abc"));
  expect(await screen.findByText("Done")).toBeDefined();
});

it("confirming happens on load, once, and a link that's been used says so", async () => {
  const act = vi.fn().mockResolvedValue({
    ok: false,
    error: {
      error: {
        code: "link_expired",
        message: "That link has expired or was already used. Ask again.",
      },
    },
  });
  render(
    <EmailLinkPage
      onLoad
      act={act}
      done={<p>Done</p>}
      failed={<p>Ask again in Settings</p>}
    />,
  );

  expect(await screen.findByText(/That link has expired/)).toBeDefined();
  expect(screen.getByText("Ask again in Settings")).toBeDefined();
  expect(act).toHaveBeenCalledOnce();
});

it("a link without its token says what to do instead", () => {
  search = "";
  const act = vi.fn();
  render(
    <EmailLinkPage
      onLoad
      act={act}
      done={<p>Done</p>}
      failed={<p>Ask again in Settings</p>}
    />,
  );

  expect(screen.getByText("Ask again in Settings")).toBeDefined();
  expect(act).not.toHaveBeenCalled();
});
