"use client";

import { Palette, Plus, Search, Shirt, SlidersHorizontal } from "lucide-react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";

import { PageLoading } from "@/components/app-shell";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { FilterPanel } from "@/components/wardrobe/filter-panel";
import {
  BottomSheet,
  BottomSheetContent,
  BottomSheetFooter,
  BottomSheetHeader,
  BottomSheetTitle,
  BottomSheetTrigger,
} from "@/components/ui/bottom-sheet";
import { Button } from "@/components/ui/button";
import { RemovableChip } from "@/components/ui/chip";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Input } from "@/components/ui/input";
import { LoadMore } from "@/components/ui/load-more";
import { PhotoTile } from "@/components/ui/photo-tile";
import { Select } from "@/components/ui/select";
import { PhotoTileSkeleton } from "@/components/ui/skeleton";
import { type Reference, useReference } from "@/lib/profile";
import { cn, focusRing } from "@/lib/utils";
import {
  type Category,
  itemDetail,
  LIST_FILTERS,
  type Sort,
  SORTS,
  useCategories,
  useItems,
  type WardrobeFilters,
} from "@/lib/wardrobe";
import {
  activeCount,
  cleared,
  filtersFrom,
  searchFrom,
  withToggled,
} from "@/lib/wardrobe-filters";

export function WardrobeContent() {
  const reference = useReference();
  const categories = useCategories();
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();
  const filters = useMemo(
    () => filtersFrom(new URLSearchParams(params.toString())),
    [params],
  );

  const apply = useCallback(
    (next: WardrobeFilters) =>
      router.replace(`${pathname}${searchFrom(next)}`, { scroll: false }),
    [router, pathname],
  );

  if (reference.isError || categories.isError) {
    return (
      <ErrorState
        title="Couldn't load your wardrobe"
        action={
          <Button
            variant="secondary"
            onClick={() => {
              void reference.refetch();
              void categories.refetch();
            }}
          >
            Try again
          </Button>
        }
      >
        Check your connection and try again.
      </ErrorState>
    );
  }
  if (!reference.data || !categories.data) return <PageLoading />;

  return (
    <Wardrobe
      filters={filters}
      reference={reference.data}
      categories={categories.data}
      onChange={apply}
    />
  );
}

function Wardrobe({
  filters,
  reference,
  categories,
  onChange,
}: {
  filters: WardrobeFilters;
  reference: Reference;
  categories: Category[];
  onChange: (filters: WardrobeFilters) => void;
}) {
  const items = useItems(filters);
  const [search, setSearch] = useState(filters.q);
  const [searched, setSearched] = useState(filters.q);
  const [sheetOpen, setSheetOpen] = useState(false);

  // When the address changes from outside (Back, a link), the box follows it.
  if (filters.q !== searched) {
    setSearched(filters.q);
    setSearch(filters.q);
  }

  // Search as the person types, once they pause.
  useEffect(() => {
    if (search === filters.q) return;
    const timer = setTimeout(() => onChange({ ...filters, q: search }), 300);
    return () => clearTimeout(timer);
  }, [search, filters, onChange]);

  const names = useMemo(() => {
    const byId = new Map<string, string>();
    for (const list of [
      reference.category_groups,
      reference.seasons,
      reference.occasions,
      reference.style_profiles,
      reference.statuses,
    ]) {
      for (const entry of list) byId.set(entry.id, entry.name);
    }
    return byId;
  }, [reference]);
  const colourNames = useMemo(
    () => new Map(reference.color_families.map((c) => [c.id, c.name])),
    [reference],
  );
  const colourHex = useMemo(
    () => new Map(reference.color_families.map((c) => [c.id, c.hex])),
    [reference],
  );
  const categoryNames = useMemo(
    () => new Map(categories.map((c) => [c.id, c.name])),
    [categories],
  );

  const pages = items.data?.pages ?? [];
  const shown = pages.flatMap((page) => page.items);
  const total = pages[0]?.total ?? 0;
  const filtering = activeCount(filters) > 0 || filters.q.trim() !== "";
  const active = LIST_FILTERS.flatMap((name) =>
    filters[name].map((value) => ({
      name,
      value,
      label:
        (name === "color" ? colourNames.get(value) : names.get(value)) ?? value,
    })),
  );

  return (
    <div className="flex flex-col gap-5">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight">
            {filters.archived ? "Archived items" : "Wardrobe"}
          </h1>
          {items.data && (
            <p className="mt-1 text-ink-soft tabular-nums" aria-live="polite">
              {total} {total === 1 ? "item" : "items"}
              {filtering ? " match" : ""}
            </p>
          )}
        </div>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="secondary">
            <Link href="/wardrobe/colours">
              <Palette aria-hidden />
              Colour map
            </Link>
          </Button>
          <Button asChild className="hidden lg:inline-flex">
            <Link href="/wardrobe/new">
              <Plus aria-hidden />
              Add item
            </Link>
          </Button>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-3">
        <div className="relative min-w-0 flex-1 basis-60">
          <Search
            aria-hidden
            className="pointer-events-none absolute top-1/2 left-3 size-5 -translate-y-1/2 text-ink-soft"
          />
          <Input
            type="search"
            value={search}
            onChange={(event) => setSearch(event.target.value)}
            placeholder="Search name, brand, colour, or type"
            aria-label="Search your wardrobe"
            className="pl-10"
          />
        </div>
        <BottomSheet open={sheetOpen} onOpenChange={setSheetOpen}>
          <BottomSheetTrigger asChild>
            <Button variant="secondary" className="lg:hidden">
              <SlidersHorizontal aria-hidden />
              Filters
              {activeCount(filters) > 0 && (
                <span className="tabular-nums">({activeCount(filters)})</span>
              )}
            </Button>
          </BottomSheetTrigger>
          <BottomSheetContent>
            <BottomSheetHeader>
              <BottomSheetTitle>Filters</BottomSheetTitle>
            </BottomSheetHeader>
            <div className="overflow-y-auto px-4 pt-4 pb-2">
              <FilterPanel
                filters={filters}
                reference={reference}
                onChange={onChange}
              />
            </div>
            <BottomSheetFooter className="border-t border-line">
              <Button onClick={() => setSheetOpen(false)}>
                Show {total} {total === 1 ? "item" : "items"}
              </Button>
            </BottomSheetFooter>
          </BottomSheetContent>
        </BottomSheet>
        <Select
          aria-label="Sort"
          value={filters.sort}
          onChange={(event) =>
            onChange({ ...filters, sort: event.target.value as Sort })
          }
          className="w-44 shrink-0"
        >
          {SORTS.map((sort) => (
            <option key={sort.id} value={sort.id}>
              {sort.name}
            </option>
          ))}
        </Select>
      </div>

      {active.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          {active.map(({ name, value, label }) => (
            <RemovableChip
              key={`${name}-${value}`}
              label={label}
              onRemove={() => onChange(withToggled(filters, name, value))}
            />
          ))}
          <Button variant="quiet" onClick={() => onChange(cleared(filters))}>
            Clear all
          </Button>
        </div>
      )}

      <div className="lg:grid lg:grid-cols-[14rem_minmax(0,1fr)] lg:gap-8">
        <aside aria-label="Filters" className="hidden lg:block">
          {/* Scrolls on its own, so every filter is reachable without scrolling the grid. */}
          <div className="sticky top-20 -m-1 max-h-[calc(100dvh-6rem)] overflow-y-auto p-1 pb-4">
            <FilterPanel
              filters={filters}
              reference={reference}
              onChange={onChange}
            />
          </div>
        </aside>
        <section aria-label="Items">
          {items.isError ? (
            <ErrorState
              title="Couldn't load your items"
              action={
                <Button
                  variant="secondary"
                  onClick={() => void items.refetch()}
                >
                  Try again
                </Button>
              }
            >
              Check your connection and try again.
            </ErrorState>
          ) : !items.data ? (
            <Grid>
              {Array.from({ length: 8 }, (_, index) => (
                <PhotoTileSkeleton key={index} />
              ))}
            </Grid>
          ) : shown.length === 0 ? (
            filtering || filters.archived ? (
              <EmptyState
                title={
                  filters.archived ? "Nothing archived" : "Nothing matches"
                }
                action={
                  filtering ? (
                    <Button
                      variant="secondary"
                      onClick={() => {
                        setSearch("");
                        onChange({ ...cleared(filters), q: "" });
                      }}
                    >
                      Clear search and filters
                    </Button>
                  ) : undefined
                }
              >
                {filters.archived
                  ? "Items you archive are kept here, out of your wardrobe and suggestions."
                  : "No item fits every filter. Remove one to see more."}
              </EmptyState>
            ) : (
              <EmptyState
                icon={<Shirt />}
                title="Your wardrobe is empty"
                action={
                  <Button asChild>
                    <Link href="/wardrobe/new">Add your first item</Link>
                  </Button>
                }
              >
                Add your first item. A photo and a colour are enough.
              </EmptyState>
            )
          ) : (
            <>
              <Grid>
                {shown.map((item) => {
                  const detail = itemDetail(item, colourNames, categoryNames);
                  return (
                    <li key={item.id}>
                      <PhotoTile
                        href={`/wardrobe/${item.id}`}
                        name={item.display_name}
                        detail={
                          item.status === "available"
                            ? detail
                            : `${names.get(item.status) ?? item.status} · ${detail}`
                        }
                      >
                        <ItemPhoto
                          photo={item.photo}
                          alt={`${item.display_name}, ${detail}`}
                          hex={
                            item.color_hex ?? colourHex.get(item.color_primary)
                          }
                        />
                      </PhotoTile>
                    </li>
                  );
                })}
              </Grid>
              <LoadMore
                shown={shown.length}
                total={total}
                loading={items.isFetchingNextPage}
                onLoadMore={() => void items.fetchNextPage()}
              />
            </>
          )}
        </section>
      </div>

      <Link
        href="/wardrobe/new"
        aria-label="Add item"
        className={cn(
          // Above the phone tab bar, as the design system places it.
          "fixed right-4 bottom-[calc(5rem+env(safe-area-inset-bottom))] z-30 grid size-14 place-content-center rounded-full bg-ink text-on-ink shadow-float transition-colors hover:bg-ink/85 lg:hidden",
          focusRing,
        )}
      >
        <Plus aria-hidden className="size-6" />
      </Link>
    </div>
  );
}

function Grid({ children }: { children: React.ReactNode }) {
  return (
    <ul className="grid grid-cols-2 gap-x-4 gap-y-6 min-[1400px]:grid-cols-5 sm:grid-cols-3 xl:grid-cols-4">
      {children}
    </ul>
  );
}
