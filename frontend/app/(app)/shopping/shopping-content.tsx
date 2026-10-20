"use client";

import { ShoppingBag } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";

import { PieceRow } from "@/components/shopping/piece-row";
import { StapleList } from "@/components/shopping/staple-list";
import { VerdictBadge } from "@/components/shopping/verdict-badge";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Skeleton } from "@/components/ui/skeleton";
import { WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { dayPhrase } from "@/lib/dates";
import { formatRupees } from "@/lib/money";
import type { Reference } from "@/lib/profile";
import {
  type Candidate,
  priceMayHaveChanged,
  STATUSES,
  useCandidates,
  useGaps,
} from "@/lib/shopping";
import { cn, focusRing } from "@/lib/utils";

const MAX_COMPARE = 4;

export function ShoppingContent() {
  return (
    <div className="flex max-w-5xl flex-col gap-8">
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="font-display text-2xl font-semibold tracking-tight">
            Shopping
          </h1>
          <p className="mt-1 text-ink-soft">
            See what something would add to your wardrobe before you buy it.
          </p>
        </div>
        <Button asChild>
          <Link href="/shopping/new">Add something</Link>
        </Button>
      </div>
      <WardrobeData>
        {({ reference }) => (
          <>
            <Gaps reference={reference} />
            <List reference={reference} />
            <Plans />
          </>
        )}
      </WardrobeData>
    </div>
  );
}

export function NeedsOccasions() {
  return (
    <Alert>
      Choose the occasions you dress for (in{" "}
      <Link
        href="/settings"
        className={cn("underline underline-offset-4", focusRing)}
      >
        Settings
      </Link>
      , or your usual week in My Week) so WearWise can tell what a piece would
      add.
    </Alert>
  );
}

function Gaps({ reference }: { reference: Reference }) {
  const gaps = useGaps();
  return (
    <section aria-labelledby="gaps-heading" className="flex flex-col gap-4">
      <div>
        <h2 id="gaps-heading" className="text-lg font-medium">
          What would add the most
        </h2>
        <p className="mt-1 max-w-prose text-sm text-ink-soft">
          Common wardrobe staples, not products: each with the good outfits it
          would make where you have few. Find them in any shop.
        </p>
      </div>
      {gaps.isError ? (
        <ErrorState
          title="Couldn't work out your gaps"
          action={
            <Button variant="secondary" onClick={() => void gaps.refetch()}>
              Try again
            </Button>
          }
        >
          Check your connection and try again.
        </ErrorState>
      ) : !gaps.data ? (
        <div aria-busy="true" className="flex flex-col gap-3">
          <Skeleton className="h-20" />
          <Skeleton className="h-20" />
          <span role="status" className="sr-only">
            Working out what would add the most
          </span>
        </div>
      ) : gaps.data.needs_occasions ? (
        <NeedsOccasions />
      ) : gaps.data.gaps.length === 0 ? (
        <p className="text-sm text-ink-soft">
          {gaps.data.covered
            ? "Every occasion and season you dress for already has plenty of good outfits."
            : "No single staple adds a good outfit where you're short. Check the occasions you dress for in Settings."}
        </p>
      ) : (
        <ul className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {gaps.data.gaps.map((gap) => (
            <li key={gap.staples.map((s) => s.id).join("+")}>
              <Card className="h-full">
                <p className="text-sm">{gap.reason}</p>
                <StapleList
                  staples={gap.staples}
                  reference={reference}
                  className="mt-3"
                />
              </Card>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

function List({ reference }: { reference: Reference }) {
  const candidates = useCandidates();
  const router = useRouter();
  const [chosen, setChosen] = useState<string[]>([]);
  const familyHex = new Map(reference.color_families.map((c) => [c.id, c.hex]));

  if (candidates.isError) {
    return (
      <ErrorState
        title="Couldn't load your shopping list"
        action={
          <Button variant="secondary" onClick={() => void candidates.refetch()}>
            Try again
          </Button>
        }
      >
        Check your connection and try again.
      </ErrorState>
    );
  }
  if (!candidates.data) {
    return <Skeleton aria-busy="true" className="h-40" />;
  }
  const rows = candidates.data.candidates;
  const toggle = (id: string) =>
    setChosen((current) =>
      current.includes(id)
        ? current.filter((x) => x !== id)
        : current.length < MAX_COMPARE
          ? [...current, id]
          : current,
    );

  return (
    <section aria-labelledby="list-heading" className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h2 id="list-heading" className="text-lg font-medium">
          Your shopping list
        </h2>
        {rows.length >= 2 && (
          <Button
            variant="secondary"
            disabled={chosen.length < 2}
            onClick={() =>
              router.push(
                `/shopping/compare?${chosen.map((id) => `id=${id}`).join("&")}`,
              )
            }
          >
            Compare{chosen.length > 0 ? ` (${chosen.length})` : ""}
          </Button>
        )}
      </div>
      {rows.length === 0 ? (
        <EmptyState
          icon={<ShoppingBag />}
          title="Nothing on your list yet"
          action={
            <Button asChild variant="secondary">
              <Link href="/shopping/new">Add something</Link>
            </Button>
          }
        >
          Add something you&apos;re thinking of buying, or a staple from the
          list above, to see what it would add.
        </EmptyState>
      ) : (
        <>
          {rows.length >= 2 && (
            <p className="text-sm text-ink-soft">
              Tick two to {MAX_COMPARE} to compare them side by side.
            </p>
          )}
          {STATUSES.map((status) => {
            const inStatus = rows.filter((row) => row.status === status.id);
            if (inStatus.length === 0) return null;
            const list = (
              <ul className="flex flex-col gap-2">
                {inStatus.map((row) => (
                  <li key={row.id}>
                    <CandidateRow
                      candidate={row}
                      familyHex={familyHex}
                      checked={chosen.includes(row.id)}
                      onCheck={
                        status.id === "purchased" || rows.length < 2
                          ? undefined
                          : () => toggle(row.id)
                      }
                    />
                  </li>
                ))}
              </ul>
            );
            const tucked = status.id === "skipped" || status.id === "purchased";
            return tucked ? (
              <details key={status.id} className="group">
                <summary
                  className={cn(
                    "min-h-11 cursor-pointer rounded-lg py-2 font-medium text-ink-soft",
                    focusRing,
                  )}
                >
                  {status.name} ({inStatus.length})
                </summary>
                <div className="mt-2">{list}</div>
              </details>
            ) : (
              <div key={status.id} className="flex flex-col gap-2">
                <h3 className="text-sm font-medium text-ink-soft">
                  {status.name}
                </h3>
                {list}
              </div>
            );
          })}
        </>
      )}
    </section>
  );
}

function CandidateRow({
  candidate,
  familyHex,
  checked,
  onCheck,
}: {
  candidate: Candidate;
  familyHex: Map<string, string | null>;
  checked: boolean;
  onCheck?: () => void;
}) {
  return (
    <div className="flex items-center gap-3 rounded-xl bg-surface p-3">
      {onCheck && (
        <Checkbox
          checked={checked}
          onCheckedChange={onCheck}
          aria-label={`Compare ${candidate.display_name}`}
        />
      )}
      <PieceRow
        className="min-w-0 flex-1"
        name={candidate.display_name}
        photo={candidate.photo}
        imageUrl={candidate.image_url}
        hex={candidate.color_hex ?? familyHex.get(candidate.color_primary)}
        href={`/shopping/${candidate.id}`}
      >
        <span className="flex flex-col items-end gap-0.5 text-right">
          {candidate.status !== "purchased" && (
            <VerdictBadge verdict={candidate.verdict} />
          )}
          {candidate.price !== null && candidate.price_checked_at && (
            <span className="text-sm text-ink-soft">
              <span className="tabular-nums">
                {formatRupees(candidate.price)}
              </span>{" "}
              · {candidate.source === "link" ? "checked" : "noted"}{" "}
              {dayPhrase(candidate.price_checked_at.slice(0, 10))}
              {priceMayHaveChanged(candidate.price_checked_at) && (
                <span className="block text-consider">May have changed</span>
              )}
            </span>
          )}
        </span>
      </PieceRow>
    </div>
  );
}

function Plans() {
  return (
    <section aria-labelledby="plans-heading" className="flex flex-col gap-4">
      <h2 id="plans-heading" className="text-lg font-medium">
        Plan your buying
      </h2>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <PlanLink
          href="/shopping/plan"
          title="Plan a starter wardrobe"
          text="A staged plan, best first, within a budget: for a small wardrobe or starting from nothing."
        />
        <PlanLink
          href="/shopping/budget"
          title="Split a budget"
          text="Which things on your list to buy for the most new outfits, without going over."
        />
      </div>
    </section>
  );
}

function PlanLink({
  href,
  title,
  text,
}: {
  href: string;
  title: string;
  text: string;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "rounded-xl transition-shadow hover:shadow-float",
        focusRing,
      )}
    >
      <Card className="h-full">
        <CardTitle>{title}</CardTitle>
        <CardDescription className="mt-1">{text}</CardDescription>
      </Card>
    </Link>
  );
}
