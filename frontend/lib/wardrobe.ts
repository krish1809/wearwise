import {
  useInfiniteQuery,
  useMutation,
  useQuery,
  useQueryClient,
} from "@tanstack/react-query";

import { api } from "@/lib/api/client";
import { ApiRequestError, readApiError } from "@/lib/api/errors";
import type { components } from "@/lib/api/schema";
import { PhotoProblem, preparePhoto } from "@/lib/photo-upload";

export type Item = components["schemas"]["ItemDetailOut"];
export type ItemSummary = components["schemas"]["ItemOut"];
export type ItemBrief = components["schemas"]["ItemBrief"];
export type NewItem = components["schemas"]["ItemCreate"];
export type ItemChanges = components["schemas"]["ItemUpdate"];
export type Photo = components["schemas"]["PhotoOut"];
export type PhotoRef = components["schemas"]["PhotoRef"];
export type Category = components["schemas"]["CategoryOut"];
export type NewCategory = components["schemas"]["CategoryCreate"];

export const SORTS = [
  { id: "newest", name: "Newest first" },
  { id: "oldest", name: "Oldest first" },
  { id: "category", name: "By category" },
] as const;
export type Sort = (typeof SORTS)[number]["id"];

/** What the wardrobe grid shows. Lists match any of their values; the filters combine. */
export type WardrobeFilters = {
  q: string;
  group: string[];
  color: string[];
  season: string[];
  occasion: string[];
  style: string[];
  status: string[];
  archived: boolean;
  sort: Sort;
  /** Only items for these outfit slots (used by the outfit studio). */
  slot?: string[];
};

export const LIST_FILTERS = [
  "group",
  "color",
  "season",
  "occasion",
  "style",
  "status",
] as const;
export type ListFilter = (typeof LIST_FILTERS)[number];

export const PAGE_SIZE = 24;

export const itemsQueryKey = ["items"] as const;
export const categoriesQueryKey = ["categories"] as const;
export const itemQueryKey = (id: string) => ["item", id] as const;

async function ok<T>(
  request: Promise<{ data?: T; error?: unknown }>,
): Promise<T> {
  const { data, error } = await request;
  if (data !== undefined) return data;
  throw new ApiRequestError(readApiError(error));
}

export function useItems(filters: WardrobeFilters) {
  return useInfiniteQuery({
    queryKey: [...itemsQueryKey, filters],
    queryFn: ({ pageParam }) =>
      ok(
        api.GET("/api/v1/items", {
          params: {
            query: {
              ...filters,
              q: filters.q || undefined,
              limit: PAGE_SIZE,
              cursor: pageParam,
            },
          },
        }),
      ),
    initialPageParam: undefined as string | undefined,
    getNextPageParam: (page) => page.next_cursor ?? undefined,
  });
}

export function useItem(id: string) {
  return useQuery({
    queryKey: itemQueryKey(id),
    queryFn: () =>
      ok(
        api.GET("/api/v1/items/{item_id}", {
          params: { path: { item_id: id } },
        }),
      ),
  });
}

export function useCategories() {
  return useQuery({
    queryKey: categoriesQueryKey,
    queryFn: () => ok(api.GET("/api/v1/categories")),
    staleTime: 5 * 60_000,
  });
}

/** After any change: the item's own page gets the new version, and every list refetches. */
function useItemSaved() {
  const queryClient = useQueryClient();
  return async (item: Item) => {
    queryClient.setQueryData(itemQueryKey(item.id), item);
    await queryClient.invalidateQueries({ queryKey: itemsQueryKey });
  };
}

export function useCreateItem() {
  const saved = useItemSaved();
  return useMutation({
    mutationFn: (body: NewItem) => ok(api.POST("/api/v1/items", { body })),
    onSuccess: saved,
  });
}

export function useUpdateItem(id: string) {
  const saved = useItemSaved();
  return useMutation({
    mutationFn: (body: ItemChanges) =>
      ok(
        api.PATCH("/api/v1/items/{item_id}", {
          params: { path: { item_id: id } },
          body,
        }),
      ),
    onSuccess: saved,
  });
}

export function useArchiveItem(id: string) {
  const saved = useItemSaved();
  return useMutation({
    mutationFn: (archive: boolean) =>
      ok(
        api.POST(
          archive
            ? "/api/v1/items/{item_id}/archive"
            : "/api/v1/items/{item_id}/restore",
          { params: { path: { item_id: id } } },
        ),
      ),
    onSuccess: saved,
  });
}

export function useDeleteItem(id: string) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      const { error, response } = await api.DELETE("/api/v1/items/{item_id}", {
        params: { path: { item_id: id } },
      });
      if (!response.ok) throw new ApiRequestError(readApiError(error));
    },
    onSuccess: async () => {
      queryClient.removeQueries({ queryKey: itemQueryKey(id) });
      await queryClient.invalidateQueries({ queryKey: itemsQueryKey });
      // Its set partners show it in their own pages.
      await queryClient.invalidateQueries({ queryKey: ["item"] });
    },
  });
}

export function useSetLink(id: string) {
  const queryClient = useQueryClient();
  const saved = useItemSaved();
  return useMutation({
    mutationFn: (otherId: string | null) =>
      ok(
        otherId
          ? api.POST("/api/v1/items/{item_id}/set", {
              params: { path: { item_id: id } },
              body: { item_id: otherId },
            })
          : api.DELETE("/api/v1/items/{item_id}/set", {
              params: { path: { item_id: id } },
            }),
      ),
    onSuccess: async (item) => {
      await saved(item);
      // The other members' pages list this one too.
      await queryClient.invalidateQueries({ queryKey: ["item"] });
    },
  });
}

/** Shrink the photo in the browser, then upload it. Problems come back as PhotoProblem. */
export function useUploadPhoto() {
  return useMutation({
    mutationFn: async (file: File): Promise<Photo> => {
      const prepared = await preparePhoto(file);
      const form = new FormData();
      form.append("file", prepared, "photo.jpg");
      const { data, error } = await api.POST("/api/v1/photos", {
        body: form as unknown as { file: string },
        bodySerializer: (body) => body as unknown as FormData,
      });
      if (data) return data;
      const problem = readApiError(error);
      throw new PhotoProblem(problem.fields.file ?? problem.message);
    },
  });
}

export function useCreateCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: NewCategory) =>
      ok(api.POST("/api/v1/categories", { body })),
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: categoriesQueryKey }),
  });
}

export function useDeleteCategory() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) => {
      const { error, response } = await api.DELETE(
        "/api/v1/categories/{category_id}",
        { params: { path: { category_id: id } } },
      );
      if (!response.ok) throw new ApiRequestError(readApiError(error));
    },
    onSuccess: () =>
      queryClient.invalidateQueries({ queryKey: categoriesQueryKey }),
  });
}

/** The categories to offer: those for the person's sections (or all), plus their own. */
export function categoriesFor(
  all: Category[],
  sections: string[],
  showAll: boolean,
): Category[] {
  if (showAll || sections.length === 0) return all;
  return all.filter(
    (category) =>
      category.custom ||
      category.sections.some((section) => sections.includes(section)),
  );
}

/** "Navy · T-shirt": the line under an item's name. */
export function itemDetail(
  item: Pick<ItemSummary, "color_primary" | "category_id">,
  colourNames: Map<string, string>,
  categoryNames: Map<string, string>,
): string {
  return [
    colourNames.get(item.color_primary),
    categoryNames.get(item.category_id),
  ]
    .filter(Boolean)
    .join(" · ");
}
