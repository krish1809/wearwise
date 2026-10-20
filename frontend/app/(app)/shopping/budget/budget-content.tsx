"use client";

import Link from "next/link";
import { useState } from "react";

import { PieceRow } from "@/components/shopping/piece-row";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { problemFrom } from "@/lib/api/errors";
import {
  AMOUNT_ERROR,
  MAX_RUPEES,
  formatRupees,
  paiseToRupeesText,
  rupeesToPaise,
} from "@/lib/money";
import type { Profile, Reference } from "@/lib/profile";
import { type Candidate, needsOccasions, useSplit } from "@/lib/shopping";
import { cn, focusRing } from "@/lib/utils";

import { NeedsOccasions } from "../shopping-content";

export function BudgetContent() {
  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <BackLink href="/shopping">Shopping</BackLink>
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Split a budget
        </h1>
        <p className="mt-1 max-w-prose text-ink-soft">
          Which things on your list to buy for the most new outfits where
          you&apos;re short, without going over. They&apos;re weighed together,
          since a shirt and trousers can make outfits neither makes alone.
        </p>
      </div>
      <WardrobeData>
        {({ reference, profile }) => (
          <Planner reference={reference} profile={profile} />
        )}
      </WardrobeData>
    </div>
  );
}

function Planner({
  reference,
  profile,
}: {
  reference: Reference;
  profile: Profile;
}) {
  const split = useSplit();
  const [budget, setBudget] = useState(
    paiseToRupeesText(profile.budget_monthly),
  );
  const [error, setError] = useState<string | undefined>();
  const familyHex = new Map(reference.color_families.map((c) => [c.id, c.hex]));

  async function run() {
    const paise = rupeesToPaise(budget);
    if (paise === null || Number.isNaN(paise) || paise > MAX_RUPEES * 100) {
      setError(paise === null ? "Enter a budget in rupees." : AMOUNT_ERROR);
      return;
    }
    setError(undefined);
    try {
      await split.mutateAsync(paise);
    } catch {
      // Shown below from split.error.
    }
  }

  const result = split.data;
  return (
    <div className="flex flex-col gap-6">
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void run();
        }}
        className="flex flex-wrap items-end gap-3"
      >
        <Field label="Budget, in rupees" error={error} className="w-56">
          {(control) => (
            <Input
              value={budget}
              onChange={(e) => setBudget(e.target.value)}
              inputMode="decimal"
              autoComplete="off"
              {...control}
            />
          )}
        </Field>
        <Button type="submit" loading={split.isPending}>
          Work it out
        </Button>
      </form>

      {needsOccasions(split.error) ? (
        <NeedsOccasions />
      ) : split.error ? (
        <Alert tone="error">{problemFrom(split.error).message}</Alert>
      ) : null}

      {result && (
        <div aria-live="polite" className="flex flex-col gap-6">
          <Card>
            <CardTitle>
              {result.chosen.length === 0
                ? "Nothing to buy within this budget"
                : `Buy ${result.chosen.length === 1 ? "this" : `these ${result.chosen.length}`}`}
            </CardTitle>
            <CardDescription className="mt-1">
              {result.chosen.length === 0
                ? "Nothing on your list that fits the budget adds a good outfit where you're short."
                : `${formatRupees(result.spent)} of ${formatRupees(result.budget)}.`}
              {!result.exhaustive &&
                " With this many things, it's a quick pick rather than every combination."}
            </CardDescription>
            <Rows rows={result.chosen} familyHex={familyHex} />
          </Card>
          {result.left.length > 0 && (
            <Card>
              <CardTitle>Not this time</CardTitle>
              <CardDescription className="mt-1">
                Over the budget with the others, or adding less.
              </CardDescription>
              <Rows rows={result.left} familyHex={familyHex} />
            </Card>
          )}
          {result.unpriced.length > 0 && (
            <Card>
              <CardTitle>Without a price</CardTitle>
              <CardDescription className="mt-1">
                Add a price to weigh these too.
              </CardDescription>
              <Rows rows={result.unpriced} familyHex={familyHex} edit />
            </Card>
          )}
        </div>
      )}
    </div>
  );
}

function Rows({
  rows,
  familyHex,
  edit = false,
}: {
  rows: Candidate[];
  familyHex: Map<string, string | null>;
  edit?: boolean;
}) {
  if (rows.length === 0) return null;
  return (
    <ul className="mt-3 flex flex-col gap-2">
      {rows.map((row) => (
        <li key={row.id}>
          <PieceRow
            name={row.display_name}
            photo={row.photo}
            hex={row.color_hex ?? familyHex.get(row.color_primary)}
            href={`/shopping/${row.id}`}
          >
            {edit ? (
              <Link
                href={`/shopping/${row.id}/edit`}
                className={cn(
                  "rounded text-sm font-medium text-indigo underline underline-offset-4",
                  focusRing,
                )}
              >
                Add a price{" "}
                <span className="sr-only">for {row.display_name}</span>
              </Link>
            ) : (
              row.price !== null && (
                <span className="text-sm tabular-nums">
                  {formatRupees(row.price)}
                </span>
              )
            )}
          </PieceRow>
        </li>
      ))}
    </ul>
  );
}
