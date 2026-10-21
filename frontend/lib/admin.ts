import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiRequestError, readApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

export type Stats = components["schemas"]["StatsOut"];

/** The owner's counts; null for everyone else (the server answers 404). */
export function useStats() {
  return useQuery({
    queryKey: ["admin", "stats"],
    retry: false,
    queryFn: async (): Promise<Stats | null> => {
      const { data, error, response } = await api.GET("/api/v1/admin/stats");
      if (data !== undefined) return data;
      if (response.status === 404) return null;
      throw new ApiRequestError(readApiError(error));
    },
  });
}
