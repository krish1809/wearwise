"use client";

import { useEffect, useState } from "react";

import { type HealthState, waitForHealth } from "@/lib/health";

// After this long without an answer, assume a sleeping server rather than a broken one.
const SLOW_AFTER_MS = 3_000;

type View = { kind: "checking" } | { kind: "waking" } | HealthState;

const MESSAGES: Record<View["kind"], string> = {
  checking: "Checking the API…",
  waking: "Waking the server. This takes up to a minute.",
  ok: "API ok, database ok",
  "database-down": "API ok, database unreachable",
  "api-down": "Can't reach the API.",
};

export function HealthStatus() {
  const [view, setView] = useState<View>({ kind: "checking" });
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    const slowTimer = setTimeout(
      () => setView({ kind: "waking" }),
      SLOW_AFTER_MS,
    );
    void waitForHealth({ signal: controller.signal }).then((result) => {
      clearTimeout(slowTimer);
      if (!controller.signal.aborted) setView(result);
    });
    return () => {
      clearTimeout(slowTimer);
      controller.abort();
    };
  }, [attempt]);

  function checkAgain() {
    setView({ kind: "checking" });
    setAttempt((count) => count + 1);
  }

  const failed = view.kind === "database-down" || view.kind === "api-down";

  return (
    <div className="space-y-3">
      <div role="status" aria-live="polite">
        <p className="text-lg">{MESSAGES[view.kind]}</p>
        {"version" in view && (
          <p className="text-sm text-neutral-600">API version {view.version}</p>
        )}
      </div>
      {failed && (
        <button
          type="button"
          onClick={checkAgain}
          className="min-h-11 rounded-lg bg-neutral-900 px-4 text-white focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-800"
        >
          Try again
        </button>
      )}
    </div>
  );
}
