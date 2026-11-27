"use client";

import { LoaderCircle } from "lucide-react";
import { useSyncExternalStore } from "react";

import { isWaking, subscribeWaking } from "@/lib/api/waking";

/**
 * Shown while a request waits for the free server to wake, so a slow first page reads as
 * "starting up" rather than broken. The status region stays in the page so screen readers
 * announce the message when it appears. It sits where toasts do, above the phone's tab bar,
 * so it never covers the header.
 */
export function WakingBanner() {
  const waking = useSyncExternalStore(subscribeWaking, isWaking, () => false);
  return (
    <div
      role="status"
      className="pointer-events-none fixed inset-x-0 bottom-24 z-50 flex justify-center px-4 lg:bottom-6"
    >
      {waking ? (
        <p className="flex items-center gap-2 rounded-full bg-surface px-4 py-2 text-sm text-ink shadow-float">
          <LoaderCircle
            aria-hidden
            className="size-4 shrink-0 animate-spin text-ink-soft"
          />
          Waking up the server, about a minute…
        </p>
      ) : null}
    </div>
  );
}
