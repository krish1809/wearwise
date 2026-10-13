"use client";

import { useEffect, useState } from "react";

import { checkHealth } from "@/lib/health";

/** True once `active` has stayed true for a while: time to say the server is waking up. */
export function useSlow(active: boolean, afterMs = 3_000): boolean {
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    if (!active) return;
    const timer = setTimeout(() => setSlow(true), afterMs);
    return () => {
      clearTimeout(timer);
      setSlow(false);
    };
  }, [active, afterMs]);
  return active && slow;
}

/**
 * Wake the backend as soon as a page that will need it opens. On the free tier it sleeps
 * after 15 idle minutes, and this way it's often awake by the time the form is sent.
 */
export function useWarmUpBackend(): void {
  useEffect(() => {
    void checkHealth();
  }, []);
}
