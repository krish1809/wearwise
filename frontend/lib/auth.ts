import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";

export type User = components["schemas"]["UserOut"];

// The backend checks the same number (backend/app/services/password_policy.py).
export const PASSWORD_MIN_LENGTH = 12;

export const meQueryKey = ["me"] as const;

/** The logged-in person, or null when nobody is. Throws only when the API can't answer. */
export async function fetchMe(): Promise<User | null> {
  const { data, response } = await api.GET("/api/v1/auth/me");
  if (data) return data;
  if (response.status === 401) return null;
  throw new Error(`Couldn't check who is logged in (HTTP ${response.status}).`);
}

export function useCurrentUser() {
  return useQuery({
    queryKey: meQueryKey,
    queryFn: fetchMe,
    staleTime: 5 * 60_000,
  });
}

/** Where to go after logging in. Only a path on this site, so a link can't send people elsewhere. */
export function safeNextPath(
  next: string | null | undefined,
  fallback = "/home",
): string {
  if (
    !next ||
    !next.startsWith("/") ||
    next.startsWith("//") ||
    next.startsWith("/\\")
  ) {
    return fallback;
  }
  return next;
}
