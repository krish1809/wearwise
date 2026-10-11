import { afterEach, describe, expect, it, vi } from "vitest";

import { api } from "@/lib/api/client";
import { checkHealth, type HealthState, waitForHealth } from "@/lib/health";

afterEach(() => {
  vi.restoreAllMocks();
});

function answer(result: { data?: unknown; error?: unknown }) {
  vi.spyOn(api, "GET").mockResolvedValue({
    response: new Response(),
    ...result,
  } as never);
}

describe("checkHealth", () => {
  it("reports ok when the API and the database are up", async () => {
    answer({ data: { status: "ok", version: "0.0.1", database: "ok" } });

    await expect(checkHealth()).resolves.toEqual({
      kind: "ok",
      version: "0.0.1",
    });
  });

  it("reports the database as down when the API answers 503", async () => {
    answer({
      error: { status: "degraded", version: "0.0.1", database: "error" },
    });

    await expect(checkHealth()).resolves.toEqual({
      kind: "database-down",
      version: "0.0.1",
    });
  });

  it("reports the API as down when the request fails", async () => {
    vi.spyOn(api, "GET").mockRejectedValue(new TypeError("fetch failed"));

    await expect(checkHealth()).resolves.toEqual({ kind: "api-down" });
  });

  it("reports the API as down when the proxy returns an error page", async () => {
    answer({ error: "<html>502 Bad Gateway</html>" });

    await expect(checkHealth()).resolves.toEqual({ kind: "api-down" });
  });
});

describe("waitForHealth", () => {
  it("keeps checking while the server wakes up", async () => {
    const check = vi
      .fn<(signal?: AbortSignal) => Promise<HealthState>>()
      .mockResolvedValueOnce({ kind: "api-down" })
      .mockResolvedValueOnce({ kind: "api-down" })
      .mockResolvedValueOnce({ kind: "ok", version: "0.0.1" });

    await expect(waitForHealth({ check, retryMs: 0 })).resolves.toEqual({
      kind: "ok",
      version: "0.0.1",
    });
    expect(check).toHaveBeenCalledTimes(3);
  });

  it("gives up when time runs out", async () => {
    const check = vi.fn(async (): Promise<HealthState> => ({
      kind: "api-down",
    }));

    await expect(waitForHealth({ check, timeoutMs: 0 })).resolves.toEqual({
      kind: "api-down",
    });
    expect(check).toHaveBeenCalledTimes(1);
  });
});
