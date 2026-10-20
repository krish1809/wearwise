"use client";

import { useState } from "react";

import { OutfitBoard } from "@/components/outfits/outfit-board";
import type { ChosenItem } from "@/components/outfits/outfit-studio";
import { dragged, PieceTray } from "@/components/outfits/piece-tray";
import { ScoreMeter } from "@/components/outfits/score-meter";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Select } from "@/components/ui/select";
import type { Reference } from "@/lib/profile";
import { type Candidate, useTry } from "@/lib/shopping";
import { cn } from "@/lib/utils";

/**
 * "What if": put the candidate with pieces you own and see that outfit's score, as if you'd
 * bought it. Nothing is saved.
 */
export function TryOn({
  candidate,
  reference,
  occasionIds,
}: {
  candidate: Candidate;
  reference: Reference;
  occasionIds: string[];
}) {
  const [chosen, setChosen] = useState<Record<string, ChosenItem>>({});
  const [occasion, setOccasion] = useState<string>(occasionIds[0] ?? "");
  const [dropping, setDropping] = useState(false);
  const ids = Object.values(chosen).map((item) => item.id);
  const tried = useTry(candidate.id, ids, occasion || null);
  const slots = reference.slots.map((slot, position) => ({
    ...slot,
    position,
  }));
  const familyHex = new Map(reference.color_families.map((c) => [c.id, c.hex]));
  // A one-piece goes with footwear and layers; anything else, with the other separates.
  const clashes =
    candidate.slot === "one_piece"
      ? ["top", "bottom", "one_piece"]
      : ["one_piece"];
  const others = slots.filter(
    (slot) =>
      slot.role === "core" &&
      slot.id !== candidate.slot &&
      !clashes.includes(slot.id),
  );
  const add = (item: ChosenItem) =>
    setChosen((current) => ({ ...current, [item.slot]: item }));
  const occasions = reference.occasions.filter((o) =>
    occasionIds.includes(o.id),
  );

  return (
    <Card>
      <CardTitle>Try it with your pieces</CardTitle>
      <CardDescription className="mt-1">
        Put it with things you own and see how that outfit scores, as if
        you&apos;d bought it.
      </CardDescription>
      <div className="mt-4 grid grid-cols-1 gap-6 md:grid-cols-[minmax(0,14rem)_minmax(0,1fr)]">
        <div className="flex flex-col gap-3">
          <div
            data-testid="try-drop"
            onDragOver={(event) => {
              if (!dragged.current) return;
              event.preventDefault();
              event.dataTransfer.dropEffect = "copy";
              setDropping(true);
            }}
            onDragLeave={() => setDropping(false)}
            onDrop={(event) => {
              event.preventDefault();
              setDropping(false);
              if (dragged.current) add(dragged.current);
              dragged.current = null;
            }}
            className={cn(
              "rounded-xl outline-2 outline-offset-4 outline-transparent motion-safe:transition-[outline-color]",
              dropping && "outline-indigo outline-dashed",
            )}
          >
            <OutfitBoard
              size="small"
              slots={slots}
              familyHex={familyHex}
              pieces={[
                {
                  slot: candidate.slot,
                  name: candidate.display_name,
                  removed: false,
                  item: {
                    color_primary: candidate.color_primary,
                    color_hex: candidate.color_hex,
                    photo: candidate.photo,
                  },
                },
                ...Object.values(chosen).map((item) => ({
                  slot: item.slot,
                  name: item.display_name,
                  removed: false,
                  item,
                })),
              ]}
            />
          </div>
          {ids.length > 0 && (
            <Button
              variant="quiet"
              className="self-start"
              onClick={() => setChosen({})}
            >
              Start again
            </Button>
          )}
        </div>
        <div className="flex flex-col gap-4">
          {occasions.length > 0 && (
            <Field label="For">
              {(control) => (
                <Select
                  value={occasion}
                  onChange={(event) => setOccasion(event.target.value)}
                  className="sm:max-w-xs"
                  {...control}
                >
                  {occasions.map((option) => (
                    <option key={option.id} value={option.id}>
                      {option.name}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          )}
          {ids.length === 0 ? (
            <p className="text-sm text-ink-soft">Add a piece or two below.</p>
          ) : tried.data?.complete && tried.data.score != null ? (
            <ScoreMeter
              score={tried.data.score}
              good={Boolean(tried.data.good)}
              reasons={tried.data.reasons}
              flat
            />
          ) : (
            <p role="status" className="text-sm text-ink-soft">
              {tried.data?.message ?? " "}
            </p>
          )}
          <PieceTray
            slots={others}
            chosenIds={ids}
            familyHex={familyHex}
            onAdd={(item) =>
              setChosen((current) => ({ ...current, [item.slot]: item }))
            }
          />
        </div>
      </div>
    </Card>
  );
}
