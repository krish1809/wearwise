"use client";

import Link from "next/link";
import { useState } from "react";

import { StapleList } from "@/components/shopping/staple-list";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { problemFrom } from "@/lib/api/errors";
import {
  AMOUNT_ERROR,
  MAX_RUPEES,
  formatRupees,
  rupeesToPaise,
} from "@/lib/money";
import type { Reference } from "@/lib/profile";
import { type CapsulePlan, needsOccasions, useCapsule } from "@/lib/shopping";
import { cn, focusRing } from "@/lib/utils";

import { NeedsOccasions } from "../shopping-content";

const STAGE_NAMES = ["First", "Next", "Then", "After that"];

export function PlanContent() {
  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <BackLink href="/shopping">Shopping</BackLink>
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Plan a starter wardrobe
        </h1>
        <p className="mt-1 max-w-prose text-ink-soft">
          A shopping plan in stages, best first: each step is the staple that
          adds the most good outfits for the occasions you dress for, given what
          you have and the steps before it. With nothing to build on, the first
          step is a whole outfit.
        </p>
      </div>
      <WardrobeData>
        {({ reference }) => <Planner reference={reference} />}
      </WardrobeData>
    </div>
  );
}

function Planner({ reference }: { reference: Reference }) {
  const capsule = useCapsule();
  const [budget, setBudget] = useState("");
  const [error, setError] = useState<string | undefined>();

  async function run() {
    const paise = rupeesToPaise(budget);
    if (paise !== null && (Number.isNaN(paise) || paise > MAX_RUPEES * 100)) {
      setError(AMOUNT_ERROR);
      return;
    }
    setError(undefined);
    try {
      await capsule.mutateAsync(paise);
    } catch {
      // Shown below from capsule.error.
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <form
        noValidate
        onSubmit={(event) => {
          event.preventDefault();
          void run();
        }}
        className="flex flex-wrap items-start gap-3"
      >
        <Field
          label="Budget, in rupees (optional)"
          hint="Left empty, the plan goes by count alone."
          error={error}
          className="w-64"
        >
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
        {/* Lined up with the input, past its label. */}
        <Button type="submit" loading={capsule.isPending} className="sm:mt-7">
          Plan it
        </Button>
      </form>

      {needsOccasions(capsule.error) ? (
        <NeedsOccasions />
      ) : capsule.error ? (
        <Alert tone="error">{problemFrom(capsule.error).message}</Alert>
      ) : null}

      {capsule.data && <Plan plan={capsule.data} reference={reference} />}
    </div>
  );
}

function Plan({
  plan,
  reference,
}: {
  plan: CapsulePlan;
  reference: Reference;
}) {
  const stages = [...new Set(plan.steps.map((step) => step.stage))];
  return (
    <div aria-live="polite" className="flex flex-col gap-6">
      {plan.budget !== null && plan.unpriced_groups.length > 0 && (
        <Alert>
          No usual spend is set for{" "}
          {plan.unpriced_groups.map((g) => g.name.toLowerCase()).join(", ")}, so
          those staples couldn&apos;t be costed and are left out. Set it in{" "}
          <Link
            href="/settings"
            className={cn("underline underline-offset-4", focusRing)}
          >
            Settings
          </Link>{" "}
          under Budget.
        </Alert>
      )}
      {plan.steps.length === 0 ? (
        <p className="text-ink-soft">
          Nothing to add: every occasion and season you dress for already has
          plenty of good outfits
          {plan.budget !== null ? ", or nothing fits the budget" : ""}.
        </p>
      ) : (
        <>
          <p className="text-ink-soft">
            {plan.steps.reduce((n, step) => n + step.staples.length, 0)} pieces
            {plan.total !== null && (
              <>
                , about {formatRupees(plan.total)} at your usual spend
                {plan.budget !== null &&
                  ` (budget ${formatRupees(plan.budget)})`}
              </>
            )}
            . Costs are your own usual spend for each kind of clothing, not
            prices.
          </p>
          {stages.map((stage) => (
            <section key={stage} className="flex flex-col gap-3">
              <h2 className="text-lg font-medium">
                {STAGE_NAMES[stage - 1] ?? `Stage ${stage}`}
              </h2>
              {plan.steps
                .filter((step) => step.stage === stage)
                .map((step) => (
                  <Card key={step.staples.map((s) => s.id).join("+")}>
                    {step.staples.length > 1 && (
                      <p className="mb-2 text-sm font-medium">
                        Together, a first outfit
                      </p>
                    )}
                    <StapleList
                      staples={step.staples}
                      reference={reference}
                      costs
                    />
                  </Card>
                ))}
            </section>
          ))}
        </>
      )}
    </div>
  );
}
