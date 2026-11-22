import { afterEach, describe, expect, it, vi } from "vitest";

import {
  createWakingFetch,
  isWaking,
  isWakingResponse,
  subscribeWaking,
} from "@/lib/api/waking";

const WAKE_URL = "https://api.example.test";

function hibernating(): Response {
  return new Response("Rate limited", {
    status: 429,
    headers: {
      "content-type": "text/plain; charset=utf-8",
      "x-render-routing": "hibernate-rate-limited",
    },
  });
}

function ourRateLimit(): Response {
  return new Response(
    JSON.stringify({ error: { code: "rate_limited", message: "Too many." } }),
    { status: 429, headers: { "content-type": "application/json" } },
  );
}

function ok(body: unknown = { ok: true }): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

type Call = { url: string; method: string; body: string | null; mode?: string };

/**
 * A pretend network: health answers from `healthAnswers` in turn (the last one repeats), the
 * direct wake-up is recorded, and every other request is asleep until health has said 200.
 */
function stubNetwork(healthAnswers: Array<() => Response>) {
  const calls: Call[] = [];
  let healthIndex = 0;
  let awake = false;
  const fetchMock = vi.fn(
    async (input: RequestInfo | URL, init?: RequestInit) => {
      const request = input instanceof Request ? input : null;
      const url = request ? request.url : String(input);
      const method = request?.method ?? init?.method ?? "GET";
      const body = request && method !== "GET" ? await request.text() : null;
      calls.push({ url, method, body, mode: init?.mode });
      if (url.startsWith(WAKE_URL)) return new Response(null, { status: 200 });
      if (url.endsWith("/api/v1/health")) {
        const make =
          healthAnswers[Math.min(healthIndex, healthAnswers.length - 1)];
        healthIndex += 1;
        const response = make();
        if (response.ok) awake = true;
        return response;
      }
      return awake ? ok({ url, method, body }) : hibernating();
    },
  );
  vi.stubGlobal("fetch", fetchMock);
  return {
    calls,
    healthChecks: () => calls.filter((c) => c.url === "/api/v1/health"),
    wakeCalls: () => calls.filter((c) => c.url.startsWith(WAKE_URL)),
  };
}

const quick = { firstDelayMs: 1, maxDelayMs: 2, timeoutMs: 200 };

afterEach(() => {
  vi.unstubAllGlobals();
  vi.unstubAllEnvs();
});

describe("isWakingResponse", () => {
  it("recognises Render's answer while the server wakes", () => {
    expect(isWakingResponse(hibernating())).toBe(true);
  });

  it("treats any 429 that isn't our JSON error as waking", () => {
    const html = new Response("<html>", {
      status: 429,
      headers: { "content-type": "text/html; charset=UTF-8" },
    });
    expect(isWakingResponse(html)).toBe(true);
  });

  it("leaves our own rate limits and other answers alone", () => {
    expect(isWakingResponse(ourRateLimit())).toBe(false);
    expect(isWakingResponse(ok())).toBe(false);
    expect(isWakingResponse(new Response("", { status: 503 }))).toBe(false);
  });
});

describe("createWakingFetch", () => {
  it("waits once for the server, then sends every request that met it asleep again", async () => {
    vi.stubEnv("NEXT_PUBLIC_BACKEND_WAKE_URL", WAKE_URL);
    const network = stubNetwork([hibernating, hibernating, () => ok()]);
    const wakingFetch = createWakingFetch(quick);

    const responses = await Promise.all(
      ["/api/v1/items", "/api/v1/outfits", "/api/v1/me"].map((path) =>
        wakingFetch(new Request(`http://site.test${path}`)),
      ),
    );

    expect(responses.map((r) => r.status)).toEqual([200, 200, 200]);
    // One shared wait: health asked until it said 200 (three times), not three times per request.
    expect(network.healthChecks()).toHaveLength(3);
    expect(network.wakeCalls()).toHaveLength(1);
    expect(network.wakeCalls()[0]).toMatchObject({
      url: `${WAKE_URL}/api/v1/health`,
      mode: "no-cors",
    });
  });

  it("sends a form's body again on the retry", async () => {
    stubNetwork([() => ok()]);
    const wakingFetch = createWakingFetch(quick);

    const response = await wakingFetch(
      new Request("http://site.test/api/v1/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: "sam@example.test" }),
      }),
    );

    expect(response.status).toBe(200);
    expect(await response.json()).toMatchObject({
      method: "POST",
      body: JSON.stringify({ email: "sam@example.test" }),
    });
  });

  it("returns our own rate limit as it is, without waiting", async () => {
    const fetchMock = vi.fn(async () => ourRateLimit());
    vi.stubGlobal("fetch", fetchMock);

    const response = await createWakingFetch(quick)(
      new Request("http://site.test/api/v1/photos"),
    );

    expect(response.status).toBe(429);
    expect(fetchMock).toHaveBeenCalledTimes(1);
  });

  it("gives back the 429 if the server doesn't wake in time", async () => {
    const network = stubNetwork([hibernating]);

    const response = await createWakingFetch(quick)(
      new Request("http://site.test/api/v1/items"),
    );

    expect(response.status).toBe(429);
    expect(network.healthChecks().length).toBeGreaterThan(1);
  });

  it("doesn't wait on a health check, since the wait itself uses them", async () => {
    const network = stubNetwork([hibernating]);

    const response = await createWakingFetch(quick)(
      new Request("http://site.test/api/v1/health"),
    );

    expect(response.status).toBe(429);
    expect(network.calls).toHaveLength(1);
  });

  it("doesn't call the backend directly when no wake-up address is set", async () => {
    vi.stubEnv("NEXT_PUBLIC_BACKEND_WAKE_URL", "");
    const network = stubNetwork([() => ok()]);

    await createWakingFetch(quick)(
      new Request("http://site.test/api/v1/items"),
    );

    expect(network.wakeCalls()).toHaveLength(0);
  });

  it("says it is waking while it waits, for the banner", async () => {
    stubNetwork([hibernating, () => ok()]);
    const seen: boolean[] = [];
    const unsubscribe = subscribeWaking(() => seen.push(isWaking()));

    await createWakingFetch(quick)(
      new Request("http://site.test/api/v1/items"),
    );
    unsubscribe();

    expect(seen).toEqual([true, false]);
    expect(isWaking()).toBe(false);
  });
});
