import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

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

export type CoverageCell = components["schemas"]["CellDetailOut"];

/** One square of the coverage map: its good outfits, or what's missing there. */
export function useCoverageCell(
  cell: { occasion: string; season: string } | null,
) {
  return useQuery({
    queryKey: ["insights", "cell", cell?.occasion, cell?.season],
    enabled: cell !== null,
    queryFn: async () => {
      const { data, error } = await api.GET(
        "/api/v1/insights/coverage/{occasion_id}/{season}",
        {
          params: {
            path: {
              occasion_id: cell?.occasion ?? "",
              season: cell?.season ?? "",
            },
          },
        },
      );
      if (data !== undefined) return data;
      throw new ApiRequestError(readApiError(error));
    },
  });
}

export type Challenge = components["schemas"]["ChallengeStatus"];
const challengeKey = ["insights", "challenge"] as const;

/** The "wear what you own" challenge, counted from the wear log since it began. */
export function useChallenge() {
  return useQuery({
    queryKey: challengeKey,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/insights/challenge");
      if (data !== undefined) return data;
      throw new ApiRequestError(readApiError(error));
    },
  });
}

export function useStartChallenge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { data, error } = await api.POST("/api/v1/insights/challenge");
      if (data !== undefined) return data;
      throw new ApiRequestError(readApiError(error));
    },
    onSuccess: (found) => queryClient.setQueryData(challengeKey, found),
  });
}

export function useStopChallenge() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { error, response } = await api.DELETE(
        "/api/v1/insights/challenge",
      );
      if (!response.ok) throw new ApiRequestError(readApiError(error));
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: challengeKey }),
  });
}
