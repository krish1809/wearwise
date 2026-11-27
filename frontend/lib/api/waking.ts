/**
 * The free backend sleeps when nobody has used it for a while. While it starts again, Render's
 * edge answers requests that come through Vercel with HTTP 429 (often with
 * `x-render-routing: hibernate-rate-limited`). Those requests never reached the API, so it is
 * safe to send them again once the server is up. This module waits for that, once for every
 * request that hit it, and tells the page so it can say what's happening.
 */

const HEALTH_PATH = "/api/v1/health";

/**
 * A 429 that didn't come from our API. The API's own rate limits answer with a JSON error body;
 * Render's and Vercel's answers while the server wakes are plain text or HTML.
 */
export function isWakingResponse(response: Response): boolean {
  if (response.status !== 429) return false;
  if (response.headers.get("x-render-routing")?.startsWith("hibernate"))
    return true;
  return !(response.headers.get("content-type") ?? "").includes(
    "application/json",
  );
}

// Whether a wait is in progress, for the banner.
let waking = false;
const listeners = new Set<() => void>();

function setWaking(value: boolean): void {
  waking = value;
  for (const listener of listeners) listener();
}

export function subscribeWaking(listener: () => void): () => void {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function isWaking(): boolean {
  return waking;
}

/**
 * Ask the backend to wake by calling it directly from this browser. Render wakes a sleeping
 * server for a direct visitor, while requests through Vercel can keep getting 429 for longer.
 * The answer is never read (`no-cors`), so no cookies or data cross over.
 */
export function wakeBackendDirectly(
  wakeUrl: string | undefined = process.env.NEXT_PUBLIC_BACKEND_WAKE_URL,
): void {
  if (!wakeUrl) return;
  globalThis
    .fetch(`${wakeUrl.replace(/\/+$/, "")}${HEALTH_PATH}`, {
      mode: "no-cors",
      cache: "no-store",
      credentials: "omit",
    })
    .catch(() => {
      // Nothing to do: the wait below finds out whether the server is up.
    });
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export type WaitOptions = {
  timeoutMs?: number;
  firstDelayMs?: number;
  maxDelayMs?: number;
};

/** Check health through the site until it answers 200, backing off from 5 to 10 seconds. */
async function pollHealth({
  timeoutMs = 120_000,
  firstDelayMs = 5_000,
  maxDelayMs = 10_000,
}: WaitOptions): Promise<boolean> {
  const deadline = Date.now() + timeoutMs;
  let delay = firstDelayMs;
  for (;;) {
    try {
      const response = await globalThis.fetch(HEALTH_PATH, {
        cache: "no-store",
      });
      if (response.ok) return true;
    } catch {
      // Not reachable yet.
    }
    if (Date.now() + delay > deadline) return false;
    await sleep(delay);
    delay = Math.min(delay * 1.5, maxDelayMs);
  }
}

let inFlight: Promise<boolean> | null = null;

/**
 * Wait until the backend answers, or about two minutes pass. Every caller shares one wait, so
 * a page that fired ten requests checks health once every few seconds, not ten times.
 */
export function waitUntilAwake(options: WaitOptions = {}): Promise<boolean> {
  if (!inFlight) {
    setWaking(true);
    wakeBackendDirectly();
    inFlight = pollHealth(options).finally(() => {
      inFlight = null;
      setWaking(false);
    });
  }
  return inFlight;
}

/**
 * The API client's fetch: a request that met a waking server waits for it, then is sent once
 * more. Health checks are passed straight through, since the wait itself uses them.
 */
export function createWakingFetch(
  options: WaitOptions = {},
): (request: Request) => Promise<Response> {
  return async (request) => {
    const isHealth =
      new URL(request.url, "http://local").pathname === HEALTH_PATH;
    // Copied before sending, because sending uses up the body.
    const retry = isHealth ? null : request.clone();
    const response = await globalThis.fetch(request);
    if (!retry || !isWakingResponse(response)) return response;
    const awake = await waitUntilAwake(options);
    return awake ? globalThis.fetch(retry) : response;
  };
}
