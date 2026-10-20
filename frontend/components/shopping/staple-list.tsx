"use client";

import { Check } from "lucide-react";

import { PieceRow } from "@/components/shopping/piece-row";
import { ShopPanel } from "@/components/shopping/shop-panel";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/toast";
import { problemFrom } from "@/lib/api/errors";
import { formatRupees } from "@/lib/money";
import type { Reference } from "@/lib/profile";
import { type Staple, useAddStaple } from "@/lib/shopping";
import { cn, focusRing } from "@/lib/utils";

/**
 * Staples (generic descriptions, not products) as rows, each with "Add to list", or a note
 * when it's already there. With `costs`, each shows the person's usual spend for its kind.
 */
export function StapleList({
  staples,
  reference,
  costs = false,
  className,
}: {
  staples: Staple[];
  reference: Reference;
  costs?: boolean;
  className?: string;
}) {
  const add = useAddStaple();
  const groups = new Map(reference.category_groups.map((g) => [g.id, g.name]));

  async function addStaple(staple: Staple) {
    try {
      await add.mutateAsync(staple.id);
      toast.success(`${staple.name} added to your list`);
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  return (
    <ul className={cn("flex flex-col gap-2", className)}>
      {staples.map((staple) => (
        <li key={staple.id}>
          <PieceRow
            name={staple.name}
            hex={staple.hex}
            label={
              <ShopPanel
                target={{ archetypeId: staple.id }}
                name={staple.name}
                trigger={
                  <button
                    type="button"
                    className={cn(
                      "max-w-full truncate rounded text-left underline decoration-line-strong underline-offset-4 hover:decoration-ink",
                      focusRing,
                    )}
                  >
                    {staple.name}
                    <span className="sr-only">: find it in shops</span>
                  </button>
                }
              />
            }
          >
            <span className="flex shrink-0 items-center gap-3">
              {costs && (
                <span className="text-right text-sm text-ink-soft">
                  {staple.usual_spend !== null ? (
                    <>
                      <span className="tabular-nums">
                        {formatRupees(staple.usual_spend)}
                      </span>
                      <span className="sr-only">
                        , your usual spend on{" "}
                        {groups.get(staple.group_id)?.toLowerCase()}
                      </span>
                    </>
                  ) : (
                    "No usual spend"
                  )}
                </span>
              )}
              {staple.on_list ? (
                <span className="inline-flex items-center gap-1 text-sm text-ink-soft">
                  <Check aria-hidden className="size-4" />
                  On your list
                </span>
              ) : (
                <Button
                  variant="secondary"
                  disabled={add.isPending}
                  onClick={() => void addStaple(staple)}
                >
                  Add to list
                  <span className="sr-only">: {staple.name}</span>
                </Button>
              )}
            </span>
          </PieceRow>
        </li>
      ))}
    </ul>
  );
}
