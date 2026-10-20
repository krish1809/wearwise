"use client";

import { useState } from "react";

import { OutfitBoard, SwatchStrip } from "@/components/outfits/outfit-board";
import { ReasonList } from "@/components/outfits/reason-list";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { problemFrom } from "@/lib/api/errors";
import {
  type Suggestion,
  type Suggestions,
  suggestionName,
  useSuggest,
} from "@/lib/suggestions";

const COUNT = 4;

type CompleteOutfitProps = {
  /** The pieces chosen so far; every option keeps them. */
  itemIds: string[];
  /** The studio's occasion, if one is chosen. */
  occasionId: string | null;
  slots: { id: string; role: string; position: number }[];
  familyHex: Map<string, string | null>;
  onUse: (suggestion: Suggestion) => void;
};

/** "Complete this outfit": the engine fills the slots still empty around the chosen pieces. */
export function CompleteOutfit({
  itemIds,
  occasionId,
  slots,
  familyHex,
  onUse,
}: CompleteOutfitProps) {
  const [open, setOpen] = useState(false);
  const [results, setResults] = useState<Suggestions | null>(null);
  const [error, setError] = useState<string | null>(null);
  const suggest = useSuggest();

  async function start() {
    setOpen(true);
    setResults(null);
    setError(null);
    try {
      setResults(
        await suggest.mutateAsync({
          occasion_id: occasionId,
          anchor_item_ids: itemIds,
          count: COUNT,
        }),
      );
    } catch (failure) {
      setError(problemFrom(failure).message);
    }
  }

  return (
    <>
      <Button
        type="button"
        variant="secondary"
        className="self-start"
        disabled={itemIds.length === 0}
        onClick={() => void start()}
      >
        Complete this outfit
      </Button>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
          <DialogHeader>
            <DialogTitle>Ways to complete it</DialogTitle>
            <DialogDescription>
              Each keeps the pieces you chose and fills the rest from your
              wardrobe.
            </DialogDescription>
          </DialogHeader>
          {error ? (
            <Alert tone="error">{error}</Alert>
          ) : !results ? (
            <div aria-busy="true" className="grid gap-6 sm:grid-cols-2">
              {[0, 1].map((key) => (
                <Skeleton key={key} className="aspect-[5/4]" />
              ))}
              <span role="status" className="sr-only">
                Finding outfits
              </span>
            </div>
          ) : results.suggestions.length === 0 ? (
            <Alert>
              {results.missing.map((missing) => missing.text).join(" ") ||
                "Nothing goes with these pieces yet."}
            </Alert>
          ) : (
            <div className="flex flex-col gap-4">
              {results.note && <Alert>{results.note}</Alert>}
              <ul className="grid gap-x-6 gap-y-8 sm:grid-cols-2">
                {results.suggestions.map((suggestion) => {
                  const pieces = suggestion.pieces.map((piece) => ({
                    slot: piece.slot,
                    name: piece.item.display_name,
                    removed: false,
                    item: piece.item,
                  }));
                  const name = suggestionName(suggestion);
                  return (
                    <li key={suggestion.id} className="flex flex-col gap-3">
                      <OutfitBoard
                        pieces={pieces}
                        slots={slots}
                        familyHex={familyHex}
                        size="small"
                        settle
                      />
                      <SwatchStrip pieces={pieces} familyHex={familyHex} />
                      <p className="font-medium">{name}</p>
                      <ReasonList reasons={suggestion.reasons} />
                      <Button
                        type="button"
                        className="self-start"
                        aria-label={`Use ${name}`}
                        onClick={() => {
                          onUse(suggestion);
                          setOpen(false);
                        }}
                      >
                        Use this
                      </Button>
                    </li>
                  );
                })}
              </ul>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
