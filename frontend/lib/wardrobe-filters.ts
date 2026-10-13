// The wardrobe's search, filters, and sort live in the address bar, so going back from an
// item returns to the same view, and a filtered view can be bookmarked.

import {
  LIST_FILTERS,
  type ListFilter,
  type Sort,
  SORTS,
  type WardrobeFilters,
} from "@/lib/wardrobe";

export function filtersFrom(params: URLSearchParams): WardrobeFilters {
  const sort = params.get("sort");
  return {
    q: params.get("q") ?? "",
    group: params.getAll("group"),
    color: params.getAll("color"),
    season: params.getAll("season"),
    occasion: params.getAll("occasion"),
    style: params.getAll("style"),
    status: params.getAll("status"),
    archived: params.get("archived") === "1",
    sort: SORTS.some((option) => option.id === sort)
      ? (sort as Sort)
      : "newest",
  };
}

export function searchFrom(filters: WardrobeFilters): string {
  const params = new URLSearchParams();
  if (filters.q.trim()) params.set("q", filters.q.trim());
  for (const name of LIST_FILTERS) {
    for (const value of filters[name]) params.append(name, value);
  }
  if (filters.archived) params.set("archived", "1");
  if (filters.sort !== "newest") params.set("sort", filters.sort);
  const query = params.toString();
  return query ? `?${query}` : "";
}

export function activeCount(filters: WardrobeFilters): number {
  return LIST_FILTERS.reduce((sum, name) => sum + filters[name].length, 0);
}

export function withToggled(
  filters: WardrobeFilters,
  name: ListFilter,
  value: string,
): WardrobeFilters {
  const values = filters[name];
  return {
    ...filters,
    [name]: values.includes(value)
      ? values.filter((existing) => existing !== value)
      : [...values, value],
  };
}

export function cleared(filters: WardrobeFilters): WardrobeFilters {
  return {
    ...filters,
    ...Object.fromEntries(LIST_FILTERS.map((name) => [name, []])),
  };
}
