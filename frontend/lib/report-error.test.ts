import { afterEach, beforeEach, expect, it, vi } from "vitest";

import { requestIds } from "@/lib/api/client";
import { reportError, resetReports } from "@/lib/report-error";

beforeEach(() => resetReports());
afterEach(() => {
  vi.unstubAllGlobals();
  window.history.replaceState(null, "", "/");
});

it("reports the page's path and the error, never the query, a few times at most", () => {
  const sent = vi.fn(async () => new Response(null, { status: 204 }));
  vi.stubGlobal("fetch", sent);
  window.history.replaceState(null, "", "/wardrobe?q=red#top");

  for (let n = 0; n < 8; n += 1) reportError(new Error(`broke ${n}`));

  expect(sent).toHaveBeenCalledTimes(5);
  const [url, init] = sent.mock.calls[0] as unknown as [string, RequestInit];
  expect(url).toBe("/api/v1/client-errors");
  const body = JSON.parse(String(init.body));
  expect(body.path).toBe("/wardrobe");
  expect(body.message).toBe("broke 0");
  expect((init.headers as Record<string, string>)["X-Requested-With"]).toBe(
    "fetch",
  );
});

it("every API request carries its own id", async () => {
  const ids = [];
  for (let n = 0; n < 2; n += 1) {
    const request = new Request("http://localhost/api/v1/health");
    const sent = (await requestIds.onRequest?.({
      request,
    } as never)) as Request;
    ids.push(sent.headers.get("X-Request-ID") ?? "");
  }

  expect(ids[0]).toMatch(/^[A-Za-z0-9-]{8,64}$/);
  expect(ids[0]).not.toBe(ids[1]);
});
