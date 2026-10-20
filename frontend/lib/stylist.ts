import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiRequestError, readApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

export type AIStatus = components["schemas"]["AIStatusOut"];
export type Thread = components["schemas"]["ThreadOut"];
export type ThreadDetail = components["schemas"]["ThreadDetailOut"];
export type ChatMessage = components["schemas"]["MessageOut"];
export type ChatCard = components["schemas"]["CardOut"];
export type ChatAction = components["schemas"]["ActionOut"];

const statusKey = ["ai", "status"] as const;
const threadsKey = ["chat", "threads"] as const;
const threadKey = (id: string) => ["chat", "thread", id] as const;

async function ok<T>(
  request: Promise<{ data?: T; error?: unknown }>,
): Promise<T> {
  const { data, error } = await request;
  if (data !== undefined) return data;
  throw new ApiRequestError(readApiError(error));
}

/** Whether the stylist and photo tagging can be used; off until a key is set. */
export function useAIStatus() {
  return useQuery({
    queryKey: statusKey,
    queryFn: () => ok(api.GET("/api/v1/ai/status")),
    staleTime: 5 * 60_000,
  });
}

export function useThreads(enabled = true) {
  return useQuery({
    queryKey: threadsKey,
    enabled,
    queryFn: () => ok(api.GET("/api/v1/chat/threads")),
  });
}

export function useThread(id: string | null) {
  return useQuery({
    queryKey: threadKey(id ?? ""),
    enabled: Boolean(id),
    queryFn: () =>
      ok(
        api.GET("/api/v1/chat/threads/{thread_id}", {
          params: { path: { thread_id: id ?? "" } },
        }),
      ),
  });
}

export function useSend() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: { thread_id?: string | null; text: string }) =>
      ok(api.POST("/api/v1/chat/messages", { body })),
    onSuccess: async (sent) => {
      queryClient.setQueryData<ThreadDetail>(
        threadKey(sent.thread.id),
        (current) => ({
          ...sent.thread,
          messages: [...(current?.messages ?? []), ...sent.messages],
        }),
      );
      await queryClient.invalidateQueries({ queryKey: threadsKey });
    },
    onError: async () => {
      // A failure may have been the day's cap: check again.
      await queryClient.invalidateQueries({ queryKey: statusKey });
    },
  });
}

export function useDeleteThread() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (id: string) =>
      ok(
        api.DELETE("/api/v1/chat/threads/{thread_id}", {
          params: { path: { thread_id: id } },
        }),
      ),
    onSuccess: async (_, id) => {
      queryClient.removeQueries({ queryKey: threadKey(id) });
      await queryClient.invalidateQueries({ queryKey: threadsKey });
    },
  });
}

/** Confirm or cancel a proposal; the thread then shows its new state. */
export function useDecide(threadId: string | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: ({ id, confirm }: { id: string; confirm: boolean }) =>
      ok(
        confirm
          ? api.POST("/api/v1/chat/actions/{action_id}/confirm", {
              params: { path: { action_id: id } },
            })
          : api.POST("/api/v1/chat/actions/{action_id}/cancel", {
              params: { path: { action_id: id } },
            }),
      ),
    onSuccess: async (action) => {
      if (threadId) {
        queryClient.setQueryData<ThreadDetail>(
          threadKey(threadId),
          (current) =>
            current
              ? {
                  ...current,
                  messages: current.messages.map((message) => ({
                    ...message,
                    cards: message.cards.map((card) =>
                      card.action?.id === action.id
                        ? { ...card, action }
                        : card,
                    ),
                  })),
                }
              : current,
        );
      }
      // Whatever it changed shows up everywhere else too.
      await Promise.all(
        [
          "outfits",
          "items",
          "item",
          "plan",
          "candidates",
          "wear-logs",
          "insights",
        ].map((key) => queryClient.invalidateQueries({ queryKey: [key] })),
      );
    },
  });
}

/** Suggestions for a photo's details, from the app's own lists only. */
export function useTagPhoto() {
  return useMutation({
    mutationFn: (photoId: string) =>
      ok(
        api.POST("/api/v1/photos/{photo_id}/tag", {
          params: { path: { photo_id: photoId } },
        }),
      ),
  });
}
