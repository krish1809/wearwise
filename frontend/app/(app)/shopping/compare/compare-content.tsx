"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";

import { VerdictBadge } from "@/components/shopping/verdict-badge";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { problemFrom } from "@/lib/api/errors";
import { formatRupees } from "@/lib/money";
import { needsOccasions, useCompare } from "@/lib/shopping";
import { cn, focusRing } from "@/lib/utils";

import { NeedsOccasions } from "../shopping-content";

type Entry = NonNullable<
  ReturnType<typeof useCompare>["data"]
>["candidates"][number];

const ROWS: { label: string; value: (entry: Entry) => React.ReactNode }[] = [
  {
    label: "Verdict",
    value: (entry) => <VerdictBadge verdict={entry.analysis.verdict} />,
  },
  {
    label: "New good outfits",
    value: (entry) =>
      entry.analysis.kind === "core"
        ? entry.analysis.new_outfits
        : `Finishes ${entry.analysis.new_outfits}`,
  },
  {
    label: "Occasions and seasons where you're short that it helps",
    value: (entry) => {
      const helped = entry.analysis.cells.filter(
        (cell) => cell.added > 0 && cell.before < 10,
      ).length;
      return helped ? `${helped} of ${entry.analysis.cells.length}` : "None";
    },
  },
  {
    label: "Price",
    value: (entry) =>
      entry.candidate.price !== null
        ? formatRupees(entry.candidate.price)
        : "Not given",
  },
  {
    label: "Cost per new outfit",
    value: (entry) =>
      entry.analysis.cost_per_new_outfit !== null
        ? formatRupees(entry.analysis.cost_per_new_outfit)
        : "—",
  },
  {
    label: "Closest you own",
    value: (entry) =>
      entry.analysis.closest
        ? `${entry.analysis.closest.display_name}, ${Math.round(entry.analysis.redundancy * 100)}% alike`
        : "Nothing like it",
  },
  {
    label: "Goes with",
    value: (entry) =>
      `${entry.analysis.matches.length} ${entry.analysis.matches.length === 1 ? "thing" : "things"} you own`,
  },
  {
    label: "Why",
    value: (entry) => entry.analysis.reasons[0]?.text,
  },
];

export function CompareContent() {
  const ids = useSearchParams().getAll("id");
  const compare = useCompare(ids);

  return (
    <div className="flex flex-col gap-6">
      <BackLink href="/shopping">Shopping</BackLink>
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        Side by side
      </h1>
      {ids.length < 2 ? (
        <p className="text-ink-soft">
          Choose two to four things on your shopping list to compare.
        </p>
      ) : needsOccasions(compare.error) ? (
        <NeedsOccasions />
      ) : compare.isError ? (
        <ErrorState
          title="Couldn't compare these"
          action={
            <Button variant="secondary" onClick={() => void compare.refetch()}>
              Try again
            </Button>
          }
        >
          {problemFrom(compare.error).message}
        </ErrorState>
      ) : !compare.data ? (
        <div aria-busy="true">
          <Skeleton className="h-80" />
          <span role="status" className="sr-only">
            Working out what each would add
          </span>
        </div>
      ) : (
        <WardrobeData>
          {({ reference }) => {
            const familyHex = new Map(
              reference.color_families.map((c) => [c.id, c.hex]),
            );
            const entries = compare.data.candidates;
            const heading = (entry: Entry, size: string) => (
              <div className="flex flex-col items-start gap-2 text-left">
                <span
                  className={cn(
                    "flex items-center justify-center rounded-lg bg-tile p-1 *:max-h-full *:max-w-full",
                    size,
                  )}
                >
                  <ItemPhoto
                    photo={entry.candidate.photo}
                    imageUrl={entry.candidate.image_url}
                    alt=""
                    hex={
                      entry.candidate.color_hex ??
                      familyHex.get(entry.candidate.color_primary)
                    }
                  />
                </span>
                <Link
                  href={`/shopping/${entry.candidate.id}`}
                  className={cn(
                    "rounded font-medium hover:underline",
                    focusRing,
                  )}
                >
                  {entry.candidate.display_name}
                </Link>
              </div>
            );
            const columns = {
              gridTemplateColumns: `repeat(${entries.length}, minmax(0, 1fr))`,
            };
            return (
              <>
                {/* Phones: each measure as a heading, the candidates side by side under it. */}
                <div className="flex flex-col gap-5 text-sm sm:hidden">
                  <div className="grid gap-3" style={columns}>
                    {entries.map((entry) => (
                      <div key={entry.candidate.id}>
                        {heading(entry, "size-16")}
                      </div>
                    ))}
                  </div>
                  <dl className="flex flex-col gap-4">
                    {ROWS.map((row) => (
                      <div key={row.label}>
                        <dt className="text-ink-soft">{row.label}</dt>
                        <dd className="mt-1 grid gap-3" style={columns}>
                          {entries.map((entry) => (
                            <span key={entry.candidate.id} className="min-w-0">
                              <span className="sr-only">
                                {entry.candidate.display_name}:{" "}
                              </span>
                              {row.value(entry)}
                            </span>
                          ))}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </div>
                <div className="hidden overflow-x-auto sm:block">
                  <table className="w-full border-separate border-spacing-x-3 border-spacing-y-2 text-sm">
                    <thead>
                      <tr>
                        <th scope="col" className="w-48">
                          <span className="sr-only">Measure</span>
                        </th>
                        {entries.map((entry) => (
                          <th
                            key={entry.candidate.id}
                            scope="col"
                            className="align-top font-medium"
                          >
                            {heading(entry, "size-20")}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {ROWS.map((row) => (
                        <tr key={row.label}>
                          <th
                            scope="row"
                            className="text-left align-top font-normal text-ink-soft"
                          >
                            {row.label}
                          </th>
                          {entries.map((entry) => (
                            <td key={entry.candidate.id} className="align-top">
                              {row.value(entry)}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </>
            );
          }}
        </WardrobeData>
      )}
    </div>
  );
}
