import {
  keepPreviousData,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiRequestError, readApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";
import { itemsQueryKey } from "@/lib/wardrobe";

export type Candidate = components["schemas"]["CandidateOut"];
export type NewCandidate = components["schemas"]["CandidateCreate"];
export type CandidateChanges = components["schemas"]["CandidateUpdate"];
export type Analysis = components["schemas"]["AnalysisOut"];
export type Staple = components["schemas"]["StapleOut"];
export type Gap = components["schemas"]["GapOut"];
export type Gaps = components["schemas"]["GapsOut"];
export type CapsulePlan = components["schemas"]["CapsuleOut"];
export type Split = components["schemas"]["SplitOut"];
export type Guide = components["schemas"]["GuideOut"];
export type Purchase = components["schemas"]["Purchase"];
export type LinkPreview = components["schemas"]["LinkPreviewOut"];
export type ShopFor = components["schemas"]["ShopOut"];
export type CatalogProduct = components["schemas"]["CatalogProductOut"];

export const candidatesQueryKey = ["candidates"] as const;
export const candidateQueryKey = (id: string) => ["candidate", id] as const;
const analysisQueryKey = (id: string) => ["candidate", id, "analysis"] as const;
const gapsQueryKey = ["shopping", "gaps"] as const;

/** Where a candidate stands, in the order the list shows them. */
export const STATUSES = [
  { id: "buy_next", name: "Buy next" },
  { id: "considering", name: "Considering" },
  { id: "later", name: "Later" },
  { id: "skipped", name: "Skipped" },
  { id: "purchased", name: "Bought" },
] as const;

async function ok<T>(
  request: Promise<{ data?: T; error?: unknown }>,
): Promise<T> {
  const { data, error } = await request;
  if (data !== undefined) return data;
  throw new ApiRequestError(readApiError(error));
}

export function useCandidates() {
  return useQuery({
    queryKey: candidatesQueryKey,
    queryFn: () => ok(api.GET("/api/v1/candidates")),
  });
}

export function useCandidate(id: string) {
  return useQuery({
    queryKey: candidateQueryKey(id),
    queryFn: () =>
      ok(
        api.GET("/api/v1/candidates/{candidate_id}", {
          params: { path: { candidate_id: id } },
        }),
      ),
  });
}

/** The analysis; it fails with "needs_occasions" until occasions are chosen. */
export function useAnalysis(id: string, enabled = true) {
  return useQuery({
    queryKey: analysisQueryKey(id),
    enabled,
    retry: (count, error) => !needsOccasions(error) && count < 2,
    queryFn: () =>
      ok(
        api.GET("/api/v1/candidates/{candidate_id}/analysis", {
          params: { path: { candidate_id: id } },
        }),
      ),
  });
}

export function useCompare(ids: string[]) {
  return useQuery({
    queryKey: ["candidates", "compare", ids],
    enabled: ids.length >= 2,
    retry: (count, error) => !needsOccasions(error) && count < 2,
    queryFn: () =>
      ok(
        api.GET("/api/v1/candidates/compare", {
          params: { query: { id: ids } },
        }),
      ),
  });
}

export function useGaps() {
  return useQuery({
    queryKey: gapsQueryKey,
    queryFn: () => ok(api.GET("/api/v1/shopping/gaps")),
  });
}

export function useGuide() {
  return useQuery({
    queryKey: ["guide"],
    queryFn: () => ok(api.GET("/api/v1/guide")),
  });
}

/** After any change to the list, the list, gaps, and that candidate refetch. */
function useListChanged() {
  const queryClient = useQueryClient();
  return async (candidate?: Candidate) => {
    if (candidate) {
      queryClient.setQueryData(candidateQueryKey(candidate.id), candidate);
    }
    await Promise.all([
      queryClient.invalidateQueries({ queryKey: candidatesQueryKey }),
      queryClient.invalidateQueries({ queryKey: gapsQueryKey }),
    ]);
  };
}

export function useCreateCandidate() {
  const changed = useListChanged();
  return useMutation({
    mutationFn: (body: NewCandidate) =>
      ok(api.POST("/api/v1/candidates", { body })),
    onSuccess: (candidate) => changed(candidate),
  });
}

export function useAddStaple() {
  const changed = useListChanged();
  return useMutation({
    mutationFn: (archetypeId: string) =>
      ok(
        api.POST("/api/v1/candidates/from-staple", {
          body: { archetype_id: archetypeId },
        }),
      ),
    onSuccess: (candidate) => changed(candidate),
  });
}

export function useUpdateCandidate(id: string) {
  const changed = useListChanged();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: CandidateChanges) =>
      ok(
        api.PATCH("/api/v1/candidates/{candidate_id}", {
          params: { path: { candidate_id: id } },
          body,
        }),
      ),
    onSuccess: async (candidate) => {
      await changed(candidate);
      await queryClient.invalidateQueries({ queryKey: analysisQueryKey(id) });
    },
  });
}

export function useDeleteCandidate(id: string) {
  const changed = useListChanged();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () =>
      ok(
        api.DELETE("/api/v1/candidates/{candidate_id}", {
          params: { path: { candidate_id: id } },
        }),
      ),
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: candidateQueryKey(id) });
      await changed();
    },
  });
}

export function usePurchase(id: string) {
  const changed = useListChanged();
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: Purchase) =>
      ok(
        api.POST("/api/v1/candidates/{candidate_id}/purchase", {
          params: { path: { candidate_id: id } },
          body,
        }),
      ),
    onSuccess: async () => {
      // The wardrobe changed, so every analysis is out of date.
      queryClient.removeQueries({ queryKey: ["candidate"] });
      await Promise.all([
        changed(),
        queryClient.invalidateQueries({ queryKey: itemsQueryKey }),
        queryClient.invalidateQueries({ queryKey: ["insights"] }),
      ]);
    },
  });
}

export function useCapsule() {
  return useMutation({
    mutationFn: (budget: number | null) =>
      ok(api.POST("/api/v1/shopping/capsule", { body: { budget } })),
  });
}

export function useSplit() {
  return useMutation({
    mutationFn: (budget: number) =>
      ok(api.POST("/api/v1/shopping/split", { body: { budget } })),
  });
}

/** True when the request failed because no occasions are chosen yet. */
export function needsOccasions(error: unknown): boolean {
  return (
    error instanceof ApiRequestError && error.problem.code === "needs_occasions"
  );
}

/** Read a pasted product page: its preview data, if the site allows it. */
export function usePreviewLink() {
  return useMutation({
    mutationFn: (url: string) =>
      ok(api.POST("/api/v1/links/preview", { body: { url } })),
  });
}

/** Shop searches and demo products for a staple or a candidate. */
export function useShop(
  target: { archetypeId: string } | { candidateId: string },
  enabled: boolean,
) {
  const query =
    "archetypeId" in target
      ? { archetype_id: target.archetypeId }
      : { candidate_id: target.candidateId };
  return useQuery({
    queryKey: ["shopping", "shop", query],
    enabled,
    queryFn: () => ok(api.GET("/api/v1/shopping/shop", { params: { query } })),
  });
}

export function useAddFromCatalog() {
  const changed = useListChanged();
  return useMutation({
    mutationFn: (productId: string) =>
      ok(
        api.POST("/api/v1/candidates/from-catalog", {
          body: { product_id: productId },
        }),
      ),
    onSuccess: (candidate) => changed(candidate),
  });
}

/** "shop.example.com" from a link, for saying where something came from. */
export function siteOf(url: string | null | undefined): string | null {
  if (!url) return null;
  try {
    return new URL(url).hostname.replace(/^www\./, "");
  } catch {
    return null;
  }
}

/** True when a price was noted or read more than a day ago. */
export function priceMayHaveChanged(
  checkedAt: string | null | undefined,
  now: Date = new Date(),
): boolean {
  if (!checkedAt) return false;
  return now.getTime() - new Date(checkedAt).getTime() > 24 * 60 * 60 * 1000;
}

export type TryResult = components["schemas"]["TryOut"];

/** The candidate with pieces you own, scored as if you'd bought it. */
export function useTry(
  candidateId: string,
  itemIds: string[],
  occasionId: string | null,
) {
  const sorted = [...itemIds].sort();
  return useQuery({
    queryKey: ["candidate", candidateId, "try", sorted, occasionId],
    enabled: sorted.length > 0,
    placeholderData: keepPreviousData,
    queryFn: () =>
      ok(
        api.POST("/api/v1/candidates/{candidate_id}/try", {
          params: { path: { candidate_id: candidateId } },
          body: { item_ids: sorted, occasion_id: occasionId },
        }),
      ),
  });
}
