"use client";

import { useWarmUpBackend } from "@/lib/hooks";

/** Renders nothing; wakes the backend so logging in right after is quick. */
export function WarmUp() {
  useWarmUpBackend();
  return null;
}
