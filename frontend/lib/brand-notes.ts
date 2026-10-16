import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiRequestError, readApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";

export type BrandNote = components["schemas"]["BrandNoteOut"];
export type BrandNoteFields = components["schemas"]["BrandNoteCreate"];

export const brandNotesQueryKey = ["brand-notes"] as const;

export function useBrandNotes() {
  return useQuery({
    queryKey: brandNotesQueryKey,
    queryFn: async () => {
      const { data, error } = await api.GET("/api/v1/brand-notes");
      if (data) return data;
      throw new ApiRequestError(readApiError(error));
    },
  });
}

/** Add a note, or change one when an id is given. */
export function useSaveBrandNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async ({
      id,
      fields,
    }: {
      id?: string;
      fields: BrandNoteFields;
    }) => {
      const { data, error } = id
        ? await api.PATCH("/api/v1/brand-notes/{note_id}", {
            params: { path: { note_id: id } },
            body: fields,
          })
        : await api.POST("/api/v1/brand-notes", { body: fields });
      if (data) return data;
      throw new ApiRequestError(readApiError(error));
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: brandNotesQueryKey }),
  });
}

export function useDeleteBrandNote() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { error, response } = await api.DELETE(
        "/api/v1/brand-notes/{note_id}",
        { params: { path: { note_id: id } } },
      );
      if (!response.ok) throw new ApiRequestError(readApiError(error));
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: brandNotesQueryKey }),
  });
}
