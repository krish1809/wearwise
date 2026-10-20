"use client";

import { Layers, Plus } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { OutfitCard } from "@/components/outfits/outfit-card";
import { Button } from "@/components/ui/button";
import { FilterChip } from "@/components/ui/chip";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { useOutfits } from "@/lib/outfits";
import type { Reference } from "@/lib/profile";

export function OutfitsContent() {
  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Outfits
        </h1>
        <div className="flex flex-wrap gap-3">
          <Button asChild variant="secondary">
            <Link href="/worn">Wear log</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href="/outfits/remix">Remix</Link>
          </Button>
          <Button asChild variant="secondary">
            <Link href="/outfits/suggest">Suggest outfits</Link>
          </Button>
          <Button asChild>
            <Link href="/outfits/new">
              <Plus aria-hidden />
              New outfit
            </Link>
          </Button>
        </div>
      </div>
      <WardrobeData>
        {({ reference }) => <OutfitGrid reference={reference} />}
      </WardrobeData>
    </div>
  );
}

function OutfitGrid({ reference }: { reference: Reference }) {
  const [favorite, setFavorite] = useState(false);
  const outfits = useOutfits({ favorite });
  const slots = reference.slots.map((slot, position) => ({
    ...slot,
    position,
  }));
  const familyHex = new Map(reference.color_families.map((c) => [c.id, c.hex]));
  const occasions = new Map(reference.occasions.map((o) => [o.id, o.name]));
  const shown = (outfits.data?.pages ?? []).flatMap((page) => page.outfits);

  return (
    <div className="flex flex-col gap-5">
      <div className="flex gap-2">
        <FilterChip selected={favorite} onClick={() => setFavorite(!favorite)}>
          Favourites only
        </FilterChip>
      </div>
      {outfits.isError ? (
        <ErrorState
          title="Couldn't load your outfits"
          action={
            <Button variant="secondary" onClick={() => void outfits.refetch()}>
              Try again
            </Button>
          }
        >
          Check your connection and try again.
        </ErrorState>
      ) : !outfits.data ? (
        <div
          aria-busy="true"
          className="grid gap-6 sm:grid-cols-2 xl:grid-cols-3"
        >
          {[0, 1, 2].map((key) => (
            <Skeleton key={key} className="aspect-[5/4]" />
          ))}
          <span role="status" className="sr-only">
            Loading
          </span>
        </div>
      ) : shown.length === 0 ? (
        favorite ? (
          <EmptyState title="No favourites yet">
            Mark an outfit as a favourite from its page, and it shows up here.
          </EmptyState>
        ) : (
          <EmptyState
            icon={<Layers />}
            title="No outfits yet"
            action={
              <Button asChild>
                <Link href="/outfits/new">Build an outfit</Link>
              </Button>
            }
          >
            Put one together from your wardrobe. A top, a bottom, and a pair of
            shoes are enough.
          </EmptyState>
        )
      ) : (
        <>
          <ul className="grid grid-cols-2 gap-x-4 gap-y-8 lg:grid-cols-3 xl:grid-cols-4">
            {shown.map((outfit) => (
              <li key={outfit.id}>
                <OutfitCard
                  outfit={outfit}
                  slots={slots}
                  familyHex={familyHex}
                  occasionName={
                    outfit.occasion_id
                      ? occasions.get(outfit.occasion_id)
                      : undefined
                  }
                />
              </li>
            ))}
          </ul>
          {outfits.hasNextPage && (
            <Button
              variant="secondary"
              className="self-center"
              loading={outfits.isFetchingNextPage}
              onClick={() => void outfits.fetchNextPage()}
            >
              Show more
            </Button>
          )}
        </>
      )}
    </div>
  );
}
