"use client";

import { Check, X } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { OutfitBoard } from "@/components/outfits/outfit-board";
import type { ChosenItem } from "@/components/outfits/outfit-studio";
import { PieceTray } from "@/components/outfits/piece-tray";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { problemFrom } from "@/lib/api/errors";
import { type Remix, useCreateOutfit, useRemix } from "@/lib/outfits";
import type { Reference } from "@/lib/profile";
import { cn, focusRing } from "@/lib/utils";

const MAX = 10;

export function RemixContent() {
  return (
    <div className="flex max-w-5xl flex-col gap-6">
      <BackLink href="/outfits">Outfits</BackLink>
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Remix
        </h1>
        <p className="mt-1 max-w-prose text-ink-soft">
          Pick up to {MAX} pieces and see the good outfits they make on their
          own, for each occasion you dress for. Handy for packing, or a week
          from a small rail.
        </p>
      </div>
      <WardrobeData>
        {({ reference }) => <RemixBoard reference={reference} />}
      </WardrobeData>
    </div>
  );
}

function RemixBoard({ reference }: { reference: Reference }) {
  const [chosen, setChosen] = useState<ChosenItem[]>([]);
  const ids = chosen.map((item) => item.id);
  const remix = useRemix(ids);
  const familyHex = new Map(reference.color_families.map((c) => [c.id, c.hex]));
  const core = reference.slots.filter((slot) => slot.role === "core");

  function add(item: ChosenItem) {
    if (ids.includes(item.id)) return;
    if (chosen.length >= MAX) {
      toast(`Up to ${MAX} pieces. Take one out to add another.`);
      return;
    }
    setChosen((current) => [...current, item]);
  }
  const remove = (item: ChosenItem) =>
    setChosen((current) => current.filter((x) => x.id !== item.id));

  return (
    <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
      <div className="flex flex-col gap-5">
        <section
          aria-labelledby="chosen-heading"
          className="flex flex-col gap-3"
        >
          <div className="flex items-center justify-between gap-3">
            <h2 id="chosen-heading" className="text-lg font-medium">
              Chosen{" "}
              <span className="text-ink-soft tabular-nums">
                ({chosen.length} of {MAX})
              </span>
            </h2>
            {chosen.length > 0 && (
              <Button variant="quiet" onClick={() => setChosen([])}>
                Clear
              </Button>
            )}
          </div>
          {chosen.length === 0 ? (
            <p className="text-sm text-ink-soft">
              Nothing yet. Press pieces below to add them.
            </p>
          ) : (
            <ul className="flex flex-wrap gap-2">
              {chosen.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => remove(item)}
                    aria-label={`Take out ${item.display_name}`}
                    className={cn(
                      "group relative flex size-16 items-center justify-center rounded-lg bg-tile p-1 *:max-h-full *:max-w-full",
                      focusRing,
                    )}
                  >
                    <ItemPhoto
                      photo={item.photo}
                      alt=""
                      hex={item.color_hex ?? familyHex.get(item.color_primary)}
                    />
                    <span className="absolute -top-1.5 -right-1.5 grid size-5 place-content-center rounded-full bg-ink text-on-ink">
                      <X aria-hidden className="size-3" />
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </section>
        <PieceTray
          slots={core}
          chosenIds={ids}
          familyHex={familyHex}
          onAdd={add}
          onRemove={remove}
          canDrag={false}
          chosenLabel="Chosen"
          hint="Press a piece to add it; press it again to take it out."
        />
      </div>
      <section
        aria-labelledby="results-heading"
        aria-live="polite"
        className="flex min-w-0 flex-col gap-4"
      >
        <h2 id="results-heading" className="sr-only">
          What they make
        </h2>
        {chosen.length < 2 ? (
          <Card>
            <p className="text-ink-soft">
              Choose at least two pieces: a top and a bottom, say, and some
              footwear.
            </p>
          </Card>
        ) : remix.isError ? (
          <Alert tone="error">{problemFrom(remix.error).message}</Alert>
        ) : !remix.data ? (
          <Skeleton className="h-48" />
        ) : (
          <Results
            remix={remix.data}
            pieces={chosen.length}
            reference={reference}
          />
        )}
      </section>
    </div>
  );
}

function Results({
  remix,
  pieces,
  reference,
}: {
  remix: Remix;
  pieces: number;
  reference: Reference;
}) {
  if (remix.needs_occasions) {
    return (
      <Alert>
        Choose the occasions you dress for in{" "}
        <Link href="/settings" className="underline">
          Settings
        </Link>{" "}
        to see what these pieces make.
      </Alert>
    );
  }
  const season =
    reference.seasons.find((s) => s.id === remix.season)?.name ?? remix.season;
  return (
    <div className="flex flex-col gap-6">
      <p className="font-medium">
        {remix.total === 0
          ? `No good outfit from these ${pieces} pieces yet, for ${season.toLowerCase()} weather.`
          : `${remix.total} good ${remix.total === 1 ? "outfit" : "outfits"} from ${pieces} pieces, for ${season.toLowerCase()} weather.`}
      </p>
      {remix.groups.map((group) => (
        <Card key={group.occasion_id}>
          <CardTitle>
            {group.occasion_name}{" "}
            <span className="font-normal text-ink-soft tabular-nums">
              · {group.count}
            </span>
          </CardTitle>
          {group.outfits.length === 0 ? (
            <p className="mt-2 text-sm text-ink-soft">
              Nothing here: these pieces don&apos;t make a good outfit at this
              level of dress.
            </p>
          ) : (
            <ul className="mt-3 grid grid-cols-2 gap-4 sm:grid-cols-3">
              {group.outfits.map((outfit) => (
                <RemixOutfit
                  key={outfit.items.map((item) => item.id).join()}
                  outfit={outfit}
                  occasionId={group.occasion_id}
                  reference={reference}
                />
              ))}
            </ul>
          )}
          {group.count > group.outfits.length && (
            <p className="mt-2 text-sm text-ink-soft">
              The best {group.outfits.length} of {group.count}.
            </p>
          )}
        </Card>
      ))}
    </div>
  );
}

function RemixOutfit({
  outfit,
  occasionId,
  reference,
}: {
  outfit: Remix["groups"][number]["outfits"][number];
  occasionId: string;
  reference: Reference;
}) {
  const create = useCreateOutfit();
  const [saved, setSaved] = useState(false);
  const slots = reference.slots.map((slot, position) => ({
    ...slot,
    position,
  }));
  const familyHex = new Map(reference.color_families.map((c) => [c.id, c.hex]));

  async function save() {
    try {
      await create.mutateAsync({
        item_ids: outfit.items.map((item) => item.id),
        name: null,
        occasion_id: occasionId,
        is_favorite: false,
      });
      setSaved(true);
      toast.success("Outfit saved");
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  return (
    <li className="flex flex-col gap-1.5">
      <OutfitBoard
        size="small"
        slots={slots}
        familyHex={familyHex}
        pieces={outfit.items.map((item) => ({
          slot: item.slot,
          name: item.display_name,
          removed: false,
          item,
        }))}
      />
      <p className="text-sm text-ink-soft">
        {outfit.items.map((item) => item.display_name).join(", ")}
      </p>
      <Button
        variant="secondary"
        className="self-start"
        disabled={saved}
        loading={create.isPending}
        onClick={() => void save()}
      >
        {saved ? (
          <>
            <Check aria-hidden />
            Saved
          </>
        ) : (
          "Save"
        )}
      </Button>
    </li>
  );
}
