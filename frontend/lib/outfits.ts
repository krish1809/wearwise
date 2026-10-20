import {
  keepPreviousData,
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiRequestError, readApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

export type Outfit = components["schemas"]["OutfitOut"];
export type OutfitPiece = components["schemas"]["OutfitPiece"];
export type OutfitCheck = components["schemas"]["OutfitCheck"];
export type NewOutfit = components["schemas"]["OutfitCreate"];
export type OutfitChanges = components["schemas"]["OutfitUpdate"];
export type WearLog = components["schemas"]["WearLogOut"];
export type NewWearLog = components["schemas"]["WearLogCreate"];
export type WearLogChanges = components["schemas"]["WearLogUpdate"];

export type OutfitFilters = { favorite: boolean; itemId?: string };
export type WearLogFilters = {
  itemId?: string;
  outfitId?: string;
  on?: string;
};

const outfitsKey = ["outfits"] as const;
const outfitKey = (id: string) => ["outfit", id] as const;
const wearLogsKey = ["wear-logs"] as const;

async function ok<T>(
  request: Promise<{ data?: T; error?: unknown }>,
): Promise<T> {
  const { data, error } = await request;
  if (data !== undefined) return data;
  throw new ApiRequestError(readApiError(error));
}

export function useOutfits(filters: OutfitFilters) {
  return useInfiniteQuery({
    queryKey: [...outfitsKey, filters],
    queryFn: ({ pageParam }) =>
      ok(
        api.GET("/api/v1/outfits", {
          params: {
            query: {
              favorite: filters.favorite || undefined,
              item_id: filters.itemId,
              cursor: pageParam,
            },
          },
        }),
      ),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
}

export function useOutfit(id: string) {
  return useQuery({
    queryKey: outfitKey(id),
    queryFn: () =>
      ok(
        api.GET("/api/v1/outfits/{outfit_id}", {
          params: { path: { outfit_id: id } },
        }),
      ),
  });
}

/** Which template the chosen items fill, and what's still needed. Changes nothing. */
export function useOutfitCheck(itemIds: string[], occasionId?: string | null) {
  const sorted = [...itemIds].sort();
  return useQuery({
    queryKey: ["outfit-check", sorted, occasionId ?? null],
    queryFn: () =>
      ok(
        api.POST("/api/v1/outfits/check", {
          body: { item_ids: sorted, occasion_id: occasionId || null },
        }),
      ),
    // Keep showing the last answer while the next one loads, so the hint doesn't flicker.
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });
}

/** Outfits, their pages, and every wear count can change together: refresh them all. */
function useRefreshWardrobe() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all(
      [outfitsKey, ["outfit"], wearLogsKey, ["items"], ["item"]].map(
        (queryKey) => queryClient.invalidateQueries({ queryKey }),
      ),
    );
}

export function useCreateOutfit() {
  const refresh = useRefreshWardrobe();
  return useMutation({
    mutationFn: (body: NewOutfit) => ok(api.POST("/api/v1/outfits", { body })),
    onSuccess: refresh,
  });
}

export function useUpdateOutfit(id: string) {
  const queryClient = useQueryClient();
  const refresh = useRefreshWardrobe();
  return useMutation({
    mutationFn: (body: OutfitChanges) =>
      ok(
        api.PATCH("/api/v1/outfits/{outfit_id}", {
          params: { path: { outfit_id: id } },
          body,
        }),
      ),
    // Favouriting answers at once on screen, and rolls back if the save fails.
    onMutate: async (body) => {
      await queryClient.cancelQueries({ queryKey: outfitKey(id) });
      const before = queryClient.getQueryData<Outfit>(outfitKey(id));
      if (
        before &&
        body.is_favorite !== undefined &&
        body.is_favorite !== null
      ) {
        queryClient.setQueryData<Outfit>(outfitKey(id), {
          ...before,
          is_favorite: body.is_favorite,
        });
      }
      return { before };
    },
    onError: (_error, _body, context) => {
      if (context?.before)
        queryClient.setQueryData(outfitKey(id), context.before);
    },
    onSuccess: async (outfit) => {
      queryClient.setQueryData(outfitKey(id), outfit);
      await refresh();
    },
  });
}

export function useDuplicateOutfit(id: string) {
  const refresh = useRefreshWardrobe();
  return useMutation({
    mutationFn: () =>
      ok(
        api.POST("/api/v1/outfits/{outfit_id}/duplicate", {
          params: { path: { outfit_id: id } },
        }),
      ),
    onSuccess: refresh,
  });
}

export function useDeleteOutfit(id: string) {
  const queryClient = useQueryClient();
  const refresh = useRefreshWardrobe();
  return useMutation({
    mutationFn: async () => {
      const { error, response } = await api.DELETE(
        "/api/v1/outfits/{outfit_id}",
        { params: { path: { outfit_id: id } } },
      );
      if (!response.ok) throw new ApiRequestError(readApiError(error));
    },
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: outfitKey(id) });
      await refresh();
    },
  });
}

export function useWearLogs(filters: WearLogFilters) {
  return useInfiniteQuery({
    queryKey: [...wearLogsKey, filters],
    queryFn: ({ pageParam }) =>
      ok(
        api.GET("/api/v1/wear-logs", {
          params: {
            query: {
              item_id: filters.itemId,
              outfit_id: filters.outfitId,
              on: filters.on,
              cursor: pageParam,
            },
          },
        }),
      ),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
}

/** Mark something as worn. Logging the same outfit twice for one day keeps one log. */
export function useLogWear() {
  const refresh = useRefreshWardrobe();
  return useMutation({
    mutationFn: (body: NewWearLog) =>
      ok(api.POST("/api/v1/wear-logs", { body })),
    onSuccess: refresh,
  });
}

export function useUpdateWearLog(id: string) {
  const refresh = useRefreshWardrobe();
  return useMutation({
    mutationFn: (body: WearLogChanges) =>
      ok(
        api.PATCH("/api/v1/wear-logs/{log_id}", {
          params: { path: { log_id: id } },
          body,
        }),
      ),
    onSuccess: refresh,
  });
}

export function useDeleteWearLog(id: string) {
  const refresh = useRefreshWardrobe();
  return useMutation({
    mutationFn: async () => {
      const { error, response } = await api.DELETE(
        "/api/v1/wear-logs/{log_id}",
        {
          params: { path: { log_id: id } },
        },
      );
      if (!response.ok) throw new ApiRequestError(readApiError(error));
    },
    onSuccess: refresh,
  });
}

export type Remix = components["schemas"]["RemixOut"];

/** The good outfits a handful of pieces make on their own, for each occasion. */
export function useRemix(itemIds: string[]) {
  const sorted = [...itemIds].sort();
  return useQuery({
    queryKey: ["outfits", "remix", sorted],
    enabled: sorted.length >= 2,
    placeholderData: keepPreviousData,
    queryFn: () =>
      ok(api.POST("/api/v1/outfits/remix", { body: { item_ids: sorted } })),
  });
}
