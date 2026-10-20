"use client";

import { Check, ThumbsDown, ThumbsUp, TriangleAlert } from "lucide-react";
import Link from "next/link";
import { useId, useState } from "react";

import {
  OutfitBoard,
  SwatchStrip,
  type BoardPiece,
} from "@/components/outfits/outfit-board";
import { ReasonList } from "@/components/outfits/reason-list";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Label } from "@/components/ui/label";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { toast } from "@/components/ui/toast";
import { problemFrom } from "@/lib/api/errors";
import { todayIso } from "@/lib/dates";
import {
  DISLIKE_REASONS,
  type DislikeReason,
  type Feedback,
  type Suggestion,
  suggestionName,
  useRateSuggestion,
  useSaveSuggestion,
  useWearSuggestion,
} from "@/lib/suggestions";

type SuggestionCardProps = {
  suggestion: Suggestion;
  slots: { id: string; role: string; position: number }[];
  familyHex: Map<string, string | null>;
  occasionName?: string;
  /** The suggestion as the API now has it, after a rating, a save, or a wear. */
  onChange: (next: Suggestion) => void;
};

/**
 * One suggested outfit: the board, its colours, why it works, and what to do with it.
 * Like and dislike change how future suggestions rank; save and wear keep it.
 */
export function SuggestionCard({
  suggestion,
  slots,
  familyHex,
  occasionName,
  onChange,
}: SuggestionCardProps) {
  const titleId = useId();
  const rate = useRateSuggestion();
  const save = useSaveSuggestion();
  const wear = useWearSuggestion();
  const [disliking, setDisliking] = useState(false);
  const name = suggestionName(suggestion);
  const pieces: BoardPiece[] = suggestion.pieces.map((piece) => ({
    slot: piece.slot,
    name: piece.item.display_name,
    removed: false,
    item: piece.item,
  }));

  async function send(feedback: Feedback | null): Promise<string | null> {
    try {
      onChange(await rate.mutateAsync({ id: suggestion.id, feedback }));
      return null;
    } catch (error) {
      return problemFrom(error).message;
    }
  }

  async function saveIt() {
    try {
      const outfit = await save.mutateAsync({ id: suggestion.id, body: {} });
      onChange({ ...suggestion, saved_outfit_id: outfit.id });
      toast.success("Outfit saved");
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  async function wearIt() {
    try {
      const log = await wear.mutateAsync({
        id: suggestion.id,
        wornOn: todayIso(),
      });
      onChange({ ...suggestion, worn_on: log.worn_on });
      toast.success("Marked as worn today");
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  return (
    <article aria-labelledby={titleId} className="flex flex-col gap-3">
      <OutfitBoard pieces={pieces} slots={slots} familyHex={familyHex} settle />
      <SwatchStrip pieces={pieces} familyHex={familyHex} />
      <div className="flex flex-col gap-1">
        <h3 id={titleId} className="font-display text-lg font-semibold">
          {name}
        </h3>
        {occasionName && (
          <p className="text-sm text-ink-soft">
            For {occasionName.toLowerCase()}
          </p>
        )}
      </div>
      {suggestion.compromise && (
        <p className="flex items-start gap-2 text-sm text-consider">
          <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
          The closest fit, a step off what the occasion usually calls for.
        </p>
      )}
      <ReasonList reasons={suggestion.reasons} />
      {suggestion.stale ? (
        <Alert>
          A piece of this outfit has been deleted or archived since it was
          suggested.
        </Alert>
      ) : (
        <div className="flex flex-wrap items-center gap-2">
          {suggestion.saved_outfit_id ? (
            <Button asChild variant="secondary">
              <Link href={`/outfits/${suggestion.saved_outfit_id}`}>
                <Check aria-hidden />
                Saved: view outfit
              </Link>
            </Button>
          ) : (
            <Button loading={save.isPending} onClick={() => void saveIt()}>
              Save outfit
            </Button>
          )}
          <Button
            variant="secondary"
            disabled={Boolean(suggestion.worn_on)}
            loading={wear.isPending}
            onClick={() => void wearIt()}
          >
            {suggestion.worn_on ? <Check aria-hidden /> : null}
            {suggestion.worn_on ? "Worn today" : "I wore this today"}
          </Button>
          <Button
            variant="quiet"
            className="px-3"
            aria-pressed={suggestion.rating === "like"}
            aria-label={`Like ${name}`}
            disabled={rate.isPending}
            onClick={async () => {
              const problem = await send(
                suggestion.rating === "like" ? null : { verdict: "like" },
              );
              if (problem) toast.error(problem);
            }}
          >
            <ThumbsUp
              aria-hidden
              className={suggestion.rating === "like" ? "fill-current" : ""}
            />
            {suggestion.rating === "like" ? "Liked" : "Like"}
          </Button>
          <Button
            variant="quiet"
            className="px-3"
            aria-pressed={suggestion.rating === "dislike"}
            aria-label={`Dislike ${name}`}
            disabled={rate.isPending}
            onClick={async () => {
              if (suggestion.rating === "dislike") {
                const problem = await send(null);
                if (problem) toast.error(problem);
              } else {
                setDisliking(true);
              }
            }}
          >
            <ThumbsDown
              aria-hidden
              className={suggestion.rating === "dislike" ? "fill-current" : ""}
            />
            {suggestion.rating === "dislike" ? "Disliked" : "Dislike"}
          </Button>
        </div>
      )}
      <DislikeDialog
        open={disliking}
        suggestion={suggestion}
        onOpenChange={setDisliking}
        onSend={send}
      />
    </article>
  );
}

function DislikeDialog({
  open,
  suggestion,
  onOpenChange,
  onSend,
}: {
  open: boolean;
  suggestion: Suggestion;
  onOpenChange: (open: boolean) => void;
  onSend: (feedback: Feedback) => Promise<string | null>;
}) {
  const [reason, setReason] = useState<DislikeReason | "">("");
  const [piece, setPiece] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const reasonsId = useId();
  const piecesId = useId();

  function reset(next: boolean) {
    onOpenChange(next);
    if (!next) {
      setReason("");
      setPiece("");
      setError(null);
    }
  }

  return (
    <Dialog open={open} onOpenChange={reset}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>What&apos;s wrong with it?</DialogTitle>
          <DialogDescription>
            Optional. It helps WearWise suggest better next time.
          </DialogDescription>
        </DialogHeader>
        <form
          noValidate
          className="flex flex-col gap-5"
          onSubmit={async (event) => {
            event.preventDefault();
            if (reason === "item" && !piece) {
              setError("Choose the piece you don't like.");
              return;
            }
            setSending(true);
            const problem = await onSend({
              verdict: "dislike",
              reason: reason || null,
              item_id: reason === "item" ? piece : null,
            });
            setSending(false);
            if (problem) setError(problem);
            else reset(false);
          }}
        >
          {error && <Alert tone="error">{error}</Alert>}
          <fieldset className="flex flex-col gap-3">
            <legend id={reasonsId} className="sr-only">
              Reason
            </legend>
            <RadioGroup
              aria-labelledby={reasonsId}
              value={reason}
              onValueChange={(value) => setReason(value as DislikeReason)}
              className="gap-3"
            >
              {DISLIKE_REASONS.map((option) => (
                <div key={option.id} className="flex items-center gap-3">
                  <RadioGroupItem
                    id={`${reasonsId}-${option.id}`}
                    value={option.id}
                  />
                  <Label
                    htmlFor={`${reasonsId}-${option.id}`}
                    className="text-base font-normal"
                  >
                    {option.label}
                  </Label>
                </div>
              ))}
            </RadioGroup>
          </fieldset>
          {reason === "item" && (
            <fieldset className="flex flex-col gap-3">
              <legend id={piecesId} className="font-medium">
                Which piece?
              </legend>
              <RadioGroup
                aria-labelledby={piecesId}
                value={piece}
                onValueChange={setPiece}
                className="gap-3"
              >
                {suggestion.pieces.map((option) => (
                  <div key={option.item.id} className="flex items-center gap-3">
                    <RadioGroupItem
                      id={`${piecesId}-${option.item.id}`}
                      value={option.item.id}
                    />
                    <Label
                      htmlFor={`${piecesId}-${option.item.id}`}
                      className="text-base font-normal"
                    >
                      {option.item.display_name}
                    </Label>
                  </div>
                ))}
              </RadioGroup>
            </fieldset>
          )}
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" loading={sending}>
              Dislike
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
