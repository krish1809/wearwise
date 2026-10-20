"use client";

import { WashingMachine } from "lucide-react";
import Link from "next/link";
import { useId, useState } from "react";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Label } from "@/components/ui/label";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { BackLink } from "@/components/wardrobe/wardrobe-data";
import { problemFrom } from "@/lib/api/errors";
import { useLaundry, useLaundryDone } from "@/lib/plan";
import { useReference } from "@/lib/profile";
import { cn, focusRing } from "@/lib/utils";

/** What's in the wash or due one; "Laundry done" makes it clean again. */
export function LaundryContent() {
  const laundry = useLaundry();
  const done = useLaundryDone();
  const reference = useReference();
  const familyHex = new Map(
    (reference.data?.color_families ?? []).map((c) => [c.id, c.hex]),
  );
  const [chosen, setChosen] = useState<Set<string>>(new Set());
  const listId = useId();

  async function finish(ids: string[]) {
    try {
      await done.mutateAsync(ids);
      setChosen(new Set());
      toast.success(
        ids.length === 1
          ? "1 item is clean again"
          : `${ids.length} items are clean again`,
      );
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <BackLink href="/week">My Week</BackLink>
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Laundry
        </h1>
        <p className="mt-2 text-ink-soft">
          What&apos;s in the wash, and what you&apos;ve worn as often as it goes
          between washes. The plan leaves these out until they&apos;re clean.
        </p>
      </div>
      {laundry.isError ? (
        <ErrorState
          title="Couldn't load the laundry"
          action={
            <Button variant="secondary" onClick={() => void laundry.refetch()}>
              Try again
            </Button>
          }
        >
          Check your connection and try again.
        </ErrorState>
      ) : !laundry.data ? (
        <div aria-busy="true" className="flex flex-col gap-2">
          {[0, 1, 2].map((key) => (
            <Skeleton key={key} className="h-16" />
          ))}
          <span role="status" className="sr-only">
            Loading
          </span>
        </div>
      ) : laundry.data.items.length === 0 ? (
        <EmptyState icon={<WashingMachine />} title="Nothing needs washing">
          Everything you&apos;ve worn still has wears left before a wash.
        </EmptyState>
      ) : (
        <div className="flex flex-col gap-4">
          <div className="flex flex-wrap gap-3">
            <Button
              loading={done.isPending}
              disabled={chosen.size === 0}
              onClick={() => void finish([...chosen])}
            >
              {chosen.size > 0
                ? `Laundry done for ${chosen.size}`
                : "Laundry done for selected"}
            </Button>
            <Button
              variant="secondary"
              loading={done.isPending && chosen.size === 0}
              onClick={() =>
                void finish(laundry.data.items.map((row) => row.item.id))
              }
            >
              All clean
            </Button>
          </div>
          <h2 id={listId} className="sr-only">
            Items to wash
          </h2>
          <ul aria-labelledby={listId} className="flex flex-col gap-2">
            {laundry.data.items.map((row) => {
              const checkboxId = `wash-${row.item.id}`;
              return (
                <li
                  key={row.item.id}
                  className="flex items-center gap-3 rounded-lg bg-surface p-2 pr-3"
                >
                  <Checkbox
                    id={checkboxId}
                    checked={chosen.has(row.item.id)}
                    onCheckedChange={(checked) => {
                      const next = new Set(chosen);
                      if (checked) next.add(row.item.id);
                      else next.delete(row.item.id);
                      setChosen(next);
                    }}
                    className="ml-2"
                  />
                  <span className="flex size-14 shrink-0 items-center justify-center rounded-md bg-tile p-1 *:max-h-full *:max-w-full">
                    <ItemPhoto
                      photo={row.item.photo}
                      alt=""
                      hex={
                        row.item.color_hex ??
                        familyHex.get(row.item.color_primary)
                      }
                    />
                  </span>
                  <Label
                    htmlFor={checkboxId}
                    className="min-w-0 flex-1 font-normal"
                  >
                    <span className="block truncate font-medium">
                      {row.item.display_name}
                    </span>
                    <span className="block text-sm text-ink-soft">
                      {row.in_laundry
                        ? "In the laundry"
                        : `Worn ${row.wears_since_wash} of ${row.wears_before_wash} times since its last wash`}
                    </span>
                  </Label>
                  <Link
                    href={`/wardrobe/${row.item.id}`}
                    className={cn(
                      "shrink-0 rounded text-sm font-medium text-indigo underline underline-offset-4",
                      focusRing,
                    )}
                  >
                    Item
                    <span className="sr-only">: {row.item.display_name}</span>
                  </Link>
                </li>
              );
            })}
          </ul>
          <p className="text-sm text-ink-soft">
            To change how many wears something goes between washes, edit the
            item.
          </p>
        </div>
      )}
    </div>
  );
}
