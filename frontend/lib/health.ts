import { api } from "@/lib/api/client";

export type HealthState =
  | { kind: "ok"; version: string }
  | { kind: "database-down"; version: string }
  | { kind: "api-down" };

/** One health check through the /api proxy. Never throws. */
export async function checkHealth(signal?: AbortSignal): Promise<HealthState> {
  try {
    const { data, error } = await api.GET("/api/v1/health", { signal });
    // A 503 carries the same body as a 200, so we can still say which part is down.
    const body = data ?? error;
    if (body?.database === "ok") return { kind: "ok", version: body.version };
    if (body?.database === "error")
      return { kind: "database-down", version: body.version };
  } catch {
    // A network failure, a proxy error page, or a cancelled request.
  }
  return { kind: "api-down" };
}

function sleep(ms: number, signal?: AbortSignal): Promise<void> {
  return new Promise((resolve) => {
    const timer = setTimeout(resolve, ms);
    signal?.addEventListener(
      "abort",
      () => {
        clearTimeout(timer);
        resolve();
      },
      { once: true },
    );
  });
}

/**
 * Check until the API answers or time runs out. On the free tier an idle backend takes about a
 * minute to wake, and requests fail until it has.
 */
export async function waitForHealth({
  signal,
  timeoutMs = 90_000,
  retryMs = 3_000,
  check = checkHealth,
}: {
  signal?: AbortSignal;
  timeoutMs?: number;
  retryMs?: number;
  check?: (signal?: AbortSignal) => Promise<HealthState>;
} = {}): Promise<HealthState> {
  const deadline = Date.now() + timeoutMs;
  for (;;) {
    const result = await check(signal);
    if (
      result.kind !== "api-down" ||
      signal?.aborted ||
      Date.now() + retryMs > deadline
    ) {
      return result;
    }
    await sleep(retryMs, signal);
  }
}
