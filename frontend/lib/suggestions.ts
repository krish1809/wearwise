import { useMutation, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiRequestError, readApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

export type Suggestion = components["schemas"]["SuggestionOut"];
export type Suggestions = components["schemas"]["SuggestionsOut"];
export type SuggestRequest = components["schemas"]["SuggestRequest"];
export type Reason = components["schemas"]["ReasonOut"];
export type Feedback = components["schemas"]["FeedbackIn"];
export type DislikeReason = NonNullable<Feedback["reason"]>;

async function ok<T>(
  request: Promise<{ data?: T; error?: unknown }>,
): Promise<T> {
  const { data, error } = await request;
  if (data !== undefined) return data;
  throw new ApiRequestError(readApiError(error));
}

/** Outfits from the engine. Each call is new suggestions, so it's a mutation, not a query. */
export function useSuggest() {
  return useMutation({
    mutationFn: (body: SuggestRequest) =>
      ok(api.POST("/api/v1/outfits/suggest", { body })),
  });
}

/** Like, dislike, or skip; or take a rating back with null. Answers the updated suggestion. */
export function useRateSuggestion() {
  return useMutation({
    mutationFn: ({
      id,
      feedback,
    }: {
      id: string;
      feedback: Feedback | null;
    }) =>
      feedback
        ? ok(
            api.POST("/api/v1/suggestions/{suggestion_id}/feedback", {
              params: { path: { suggestion_id: id } },
              body: feedback,
            }),
          )
        : ok(
            api.DELETE("/api/v1/suggestions/{suggestion_id}/feedback", {
              params: { path: { suggestion_id: id } },
            }),
          ),
  });
}

/** Saving or wearing changes outfits, the wear log, and wear counts: refresh them all. */
function useRefreshWardrobe() {
  const queryClient = useQueryClient();
  return () =>
    Promise.all(
      [["outfits"], ["outfit"], ["wear-logs"], ["items"], ["item"]].map(
        (queryKey) => queryClient.invalidateQueries({ queryKey }),
      ),
    );
}

export function useSaveSuggestion() {
  const refresh = useRefreshWardrobe();
  return useMutation({
    mutationFn: ({
      id,
      body,
    }: {
      id: string;
      body: components["schemas"]["SaveIn"];
    }) =>
      ok(
        api.POST("/api/v1/suggestions/{suggestion_id}/save", {
          params: { path: { suggestion_id: id } },
          body,
        }),
      ),
    onSuccess: refresh,
  });
}

export function useWearSuggestion() {
  const refresh = useRefreshWardrobe();
  return useMutation({
    mutationFn: ({ id, wornOn }: { id: string; wornOn: string }) =>
      ok(
        api.POST("/api/v1/suggestions/{suggestion_id}/wear", {
          params: { path: { suggestion_id: id } },
          body: { worn_on: wornOn },
        }),
      ),
    onSuccess: refresh,
  });
}

/** What a dislike can be about, in the order the dialog offers them. */
export const DISLIKE_REASONS: { id: DislikeReason; label: string }[] = [
  { id: "item", label: "I don't like one of the pieces" },
  { id: "colors", label: "The colours don't work" },
  { id: "formality", label: "Too dressy or too casual together" },
  { id: "occasion", label: "Not right for the occasion" },
  { id: "other", label: "Something else" },
];

/**
 * "White shirt, beige chinos and brown loafers": the core pieces apart from the layer, so
 * suggestions that differ only in their shoes don't share a name.
 */
export function suggestionName(suggestion: Suggestion): string {
  const names = suggestion.pieces
    .filter((piece) => piece.core && piece.slot !== "layer")
    .map((piece, index) =>
      index === 0 || /^[A-Z]{2}/.test(piece.item.display_name)
        ? piece.item.display_name
        : piece.item.display_name.charAt(0).toLowerCase() +
          piece.item.display_name.slice(1),
    );
  if (names.length === 0) return "Outfit";
  if (names.length === 1) return names[0];
  return `${names.slice(0, -1).join(", ")} and ${names[names.length - 1]}`;
}
