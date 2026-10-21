import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiRequestError, readApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

export type Stats = components["schemas"]["StatsOut"];
export type AgentTrend = components["schemas"]["TrendOut"];
export type AgentTrends = components["schemas"]["TrendsOut"];
export type AgentRun = components["schemas"]["RunOut"];
export type AgentRuns = components["schemas"]["RunsOut"];
export type TrendStatus = "pending" | "approved" | "rejected" | "expired";
export type TrendDecision = components["schemas"]["TrendDecision"]["status"];
export type RunKind = "trend_scout" | "weekly_digest";

const adminQueryKey = ["admin"] as const;

/** The owner's counts; null for everyone else (the server answers 404). */
export function useStats() {
  return useQuery({
    queryKey: [...adminQueryKey, "stats"],
    retry: false,
    queryFn: async (): Promise<Stats | null> => {
      const { data, error, response } = await api.GET("/api/v1/admin/stats");
      if (data !== undefined) return data;
      if (response.status === 404) return null;
      throw new ApiRequestError(readApiError(error));
    },
  });
}

/** Trends the Trend Scout found, with their sources; null for anyone but the owner. */
export function useTrends(status: TrendStatus) {
  return useQuery({
    queryKey: [...adminQueryKey, "trends", status],
    retry: false,
    queryFn: async (): Promise<AgentTrends | null> => {
      const { data, error, response } = await api.GET("/api/v1/admin/trends", {
        params: { query: { status } },
      });
      if (data !== undefined) return data;
      if (response.status === 404) return null;
      throw new ApiRequestError(readApiError(error));
    },
  });
}

export function useDecideTrend() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      status,
    }: {
      id: string;
      status: TrendDecision;
    }): Promise<AgentTrend> => {
      const { data, error } = await api.PATCH(
        "/api/v1/admin/trends/{trend_id}",
        { params: { path: { trend_id: id } }, body: { status } },
      );
      if (data !== undefined) return data;
      throw new ApiRequestError(readApiError(error));
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: [...adminQueryKey, "trends"] }),
  });
}

/** One agent's latest runs, newest first; null for anyone but the owner. */
export function useRuns(kind: RunKind) {
  return useQuery({
    queryKey: [...adminQueryKey, "runs", kind],
    retry: false,
    queryFn: async (): Promise<AgentRuns | null> => {
      const { data, error, response } = await api.GET("/api/v1/admin/runs", {
        params: { query: { kind } },
      });
      if (data !== undefined) return data;
      if (response.status === 404) return null;
      throw new ApiRequestError(readApiError(error));
    },
  });
}

// Why a run stopped early, in words (the same as the owner's run report).
const STOPPED: Record<string, string> = {
  search_credits: "the month's search credits ran out",
  time: "it reached its time limit",
  tokens: "it reached its token limit",
  model_off: "the model is switched off",
  model_unavailable: "the model didn't answer",
  model_unreadable: "the model's answer couldn't be read",
  spend_cap: "today's AI spend cap was reached",
  search_unavailable: "the search service didn't answer",
  lapsed: "it never said it had finished",
  batch_cap: "it reached the most emails one run sends",
};

export function stoppedBecause(reason: string | null | undefined): string {
  if (!reason) return "";
  return STOPPED[reason] ?? reason;
}
