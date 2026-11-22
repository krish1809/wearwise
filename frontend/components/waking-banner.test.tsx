import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { createWakingFetch } from "@/lib/api/waking";
import { WakingBanner } from "@/components/waking-banner";

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("WakingBanner", () => {
  it("shows while a request waits for the server, and goes when it is up", async () => {
    let healthy = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (input: RequestInfo | URL) => {
        const url = input instanceof Request ? input.url : String(input);
        if (url.endsWith("/api/v1/health")) {
          return new Response("{}", { status: healthy ? 200 : 503 });
        }
        return healthy
          ? new Response("{}", { status: 200 })
          : new Response("asleep", {
              status: 429,
              headers: { "x-render-routing": "hibernate-rate-limited" },
            });
      }),
    );
    render(<WakingBanner />);
    expect(screen.queryByText(/Waking up the server/)).toBeNull();

    let pending!: Promise<Response>;
    await act(async () => {
      pending = createWakingFetch({ firstDelayMs: 5, maxDelayMs: 5 })(
        new Request("http://site.test/api/v1/items"),
      );
    });
    expect(screen.getByRole("status").textContent).toBe(
      "Waking up the server, about a minute…",
    );

    healthy = true;
    await act(async () => {
      await pending;
    });
    expect(screen.queryByText(/Waking up the server/)).toBeNull();
  });
});
