import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import type { components } from "@/lib/api/schema";
import { useHydrated } from "@/lib/hooks";

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
  const query = useQuery({
    queryKey: meQueryKey,
    queryFn: fetchMe,
    staleTime: 5 * 60_000,
  });
  // The shell fetches the user before pages hydrate; pages must still hydrate as the server
  // rendered them (waiting for the user), then show the user.
  const hydrated = useHydrated();
  return hydrated ? query : { ...query, data: undefined };
}

// Any origin will do: the path is resolved against it only to see whether it stays there.
const HERE = "https://wearwise.invalid";

/**
 * Where to go after logging in. Only a path on this site, so a link can't send people elsewhere.
 * The path is read the way the browser will read it (which drops tabs and line breaks, so
 * "/\t/elsewhere" becomes "//elsewhere"), and refused unless it stays on this site.
 */
export function safeNextPath(
  next: string | null | undefined,
  fallback = "/home",
): string {
  if (!next || !next.startsWith("/")) return fallback;
  try {
    const url = new URL(next, HERE);
    return url.origin === HERE
      ? `${url.pathname}${url.search}${url.hash}`
      : fallback;
  } catch {
    return fallback;
  }
}
