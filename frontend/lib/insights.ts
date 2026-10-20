import { useQuery } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiRequestError, readApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

export type Insights = components["schemas"]["InsightsOut"];
export type WornRow = components["schemas"]["WornOut"];
export type CostRow = components["schemas"]["CostOut"];

export function useInsights() {
  return useQuery({
    queryKey: ["insights"],
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/insights");
      if (data !== undefined) return data;
      throw new ApiRequestError(readApiError(error));
    },
  });
}

/** "Oct 2026" from "2026-10". */
export function monthLabel(month: string): string {
  return new Date(`${month}-01T00:00:00`).toLocaleDateString("en-IN", {
    month: "short",
    year: "numeric",
  });
}

/** A share between 0 and 1 as a whole percentage. */
export function percent(share: number): string {
  return `${Math.round(share * 100)}%`;
}
