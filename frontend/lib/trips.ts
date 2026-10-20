import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiRequestError, readApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

export type Trip = components["schemas"]["TripOut"];
export type TripSummary = components["schemas"]["TripSummary"];
export type NewTrip = components["schemas"]["TripIn"];

const tripKey = (id: string) => ["trip", id] as const;

async function ok<T>(
  request: Promise<{ data?: T; error?: unknown }>,
): Promise<T> {
  const { data, error } = await request;
  if (data !== undefined) return data;
  throw new ApiRequestError(readApiError(error));
}

export function useTrips() {
  return useQuery({
    queryKey: ["trips"],
    queryFn: () => ok(api.GET("/api/v1/trips")),
  });
}

export function useTrip(id: string) {
  return useQuery({
    queryKey: tripKey(id),
    queryFn: () =>
      ok(
        api.GET("/api/v1/trips/{trip_id}", {
          params: { path: { trip_id: id } },
        }),
      ),
  });
}

export function useCreateTrip() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: NewTrip) => ok(api.POST("/api/v1/trips", { body })),
    onSuccess: async (trip) => {
      queryClient.setQueryData(tripKey(trip.id), trip);
      await queryClient.invalidateQueries({ queryKey: ["trips"] });
    },
  });
}

/** Packing changes item statuses, so the wardrobe and plan refresh too. */
function useRefreshAfterPacking() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all(
      [["trips"], ["items"], ["item"], ["plan"]].map((queryKey) =>
        queryClient.invalidateQueries({ queryKey }),
      ),
    );
}

export function useMarkPacked(id: string) {
  const queryClient = useQueryClient();
  const refresh = useRefreshAfterPacking();
  return useMutation({
    mutationFn: (body: { item_ids: string[]; packed: boolean }) =>
      ok(
        api.POST("/api/v1/trips/{trip_id}/packed", {
          params: { path: { trip_id: id } },
          body,
        }),
      ),
    onSuccess: async (trip) => {
      queryClient.setQueryData(tripKey(id), trip);
      await refresh();
    },
  });
}

export function useReplanTrip(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      ok(
        api.POST("/api/v1/trips/{trip_id}/replan", {
          params: { path: { trip_id: id } },
        }),
      ),
    onSuccess: (trip) => queryClient.setQueryData(tripKey(id), trip),
  });
}

export function useDeleteTrip(id: string) {
  const queryClient = useQueryClient();
  const refresh = useRefreshAfterPacking();
  return useMutation({
    mutationFn: async () => {
      const { error, response } = await api.DELETE("/api/v1/trips/{trip_id}", {
        params: { path: { trip_id: id } },
      });
      if (!response.ok) throw new ApiRequestError(readApiError(error));
    },
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: tripKey(id) });
      await refresh();
    },
  });
}
