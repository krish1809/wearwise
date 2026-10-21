import {
  cleanup,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { Toaster } from "@/components/ui/toast";

import { DownloadData } from "./download-data";

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

it("saves the zip under the name the server gives it", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(
      async () =>
        new Response("zip", {
          status: 200,
          headers: {
            "content-type": "application/zip",
            "content-disposition":
              'attachment; filename="wearwise-2026-10-21.zip"',
          },
        }),
    ),
  );
  URL.createObjectURL = vi.fn(() => "blob:export");
  URL.revokeObjectURL = vi.fn();
  const clicked: string[] = [];
  vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
    this: HTMLAnchorElement,
  ) {
    clicked.push(this.download);
  });
  render(<DownloadData />);

  fireEvent.click(screen.getByRole("button", { name: "Download my data" }));

  await waitFor(() => expect(clicked).toEqual(["wearwise-2026-10-21.zip"]));
  expect(fetch).toHaveBeenCalledWith("/api/v1/account/export");
});

it("says why when the server refuses", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      Response.json(
        {
          error: {
            code: "rate_limited",
            message:
              "You've downloaded your data a few times this hour. Try again later.",
          },
        },
        { status: 429 },
      ),
    ),
  );
  render(
    <>
      <DownloadData />
      <Toaster />
    </>,
  );

  fireEvent.click(screen.getByRole("button", { name: "Download my data" }));

  expect(
    await screen.findByText(
      "You've downloaded your data a few times this hour. Try again later.",
    ),
  ).toBeDefined();
});
