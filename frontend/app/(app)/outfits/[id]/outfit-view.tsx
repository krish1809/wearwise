"use client";

import { Copy, Pencil, Star } from "lucide-react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { PageLoading } from "@/components/app-shell";
import { MarkWorn } from "@/components/outfits/mark-worn";
import { OutfitBoard, SwatchStrip } from "@/components/outfits/outfit-board";
import { ReasonList } from "@/components/outfits/reason-list";
import { WearLogList } from "@/components/outfits/wear-log-list";
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
  DialogTrigger,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { toast } from "@/components/ui/toast";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { ApiRequestError, problemFrom } from "@/lib/api/errors";
import { dayPhrase, todayIso } from "@/lib/dates";
import {
  type Outfit,
  useDeleteOutfit,
  useDuplicateOutfit,
  useOutfit,
  useUpdateOutfit,
} from "@/lib/outfits";
import type { Reference } from "@/lib/profile";
import { cn, focusRing } from "@/lib/utils";

export function OutfitView() {
  const { id } = useParams<{ id: string }>();
  const outfit = useOutfit(id);

  if (
    outfit.error instanceof ApiRequestError &&
    outfit.error.problem.code === "outfit_not_found"
  ) {
    return (
      <EmptyState
        title="That outfit doesn't exist"
        action={
          <Button asChild variant="secondary">
            <Link href="/outfits">Back to your outfits</Link>
          </Button>
        }
      >
        It may have been deleted.
      </EmptyState>
    );
  }
  if (outfit.isError) {
    return (
      <ErrorState
        title="Couldn't load this outfit"
        action={
          <Button variant="secondary" onClick={() => void outfit.refetch()}>
            Try again
          </Button>
        }
      >
        Check your connection and try again.
      </ErrorState>
    );
  }
  if (!outfit.data) return <PageLoading />;
  const loaded = outfit.data;

  return (
    <WardrobeData>
      {({ reference }) => <Details outfit={loaded} reference={reference} />}
    </WardrobeData>
  );
}

function Details({
  outfit,
  reference,
}: {
  outfit: Outfit;
  reference: Reference;
}) {
  const router = useRouter();
  const update = useUpdateOutfit(outfit.id);
  const duplicate = useDuplicateOutfit(outfit.id);
  const slots = reference.slots.map((slot, position) => ({
    ...slot,
    position,
  }));
  const familyHex = new Map(reference.color_families.map((c) => [c.id, c.hex]));
  const occasion = reference.occasions.find(
    (o) => o.id === outfit.occasion_id,
  )?.name;
  const present = outfit.pieces.filter((piece) => piece.item);

  async function toggleFavourite() {
    try {
      await update.mutateAsync({ is_favorite: !outfit.is_favorite });
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  async function copy() {
    try {
      const made = await duplicate.mutateAsync();
      toast.success("Copy saved");
      router.push(`/outfits/${made.id}`);
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  return (
    <div className="flex flex-col gap-6">
      <BackLink href="/outfits">Outfits</BackLink>
      <div className="grid grid-cols-1 gap-8 lg:grid-cols-[minmax(0,26rem)_minmax(0,1fr)]">
        <div className="flex flex-col gap-3">
          <OutfitBoard
            pieces={outfit.pieces}
            slots={slots}
            familyHex={familyHex}
          />
          <SwatchStrip pieces={outfit.pieces} familyHex={familyHex} />
          {outfit.reasons.length > 0 && (
            <section aria-labelledby="why-heading" className="mt-2">
              <h2 id="why-heading" className="mb-2 font-medium">
                Why it works
              </h2>
              <ReasonList reasons={outfit.reasons} />
            </section>
          )}
        </div>
        <div className="flex min-w-0 flex-col gap-6">
          <div className="flex items-start justify-between gap-3">
            <div className="min-w-0">
              <h1 className="font-display text-2xl font-semibold tracking-tight break-words">
                {outfit.display_name}
              </h1>
              <p className="mt-1 text-ink-soft">
                {[
                  occasion,
                  outfit.last_worn_on
                    ? `Worn ${outfit.wear_count} ${outfit.wear_count === 1 ? "time" : "times"}, last ${dayPhrase(outfit.last_worn_on)}`
                    : "Not worn yet",
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </p>
            </div>
            <button
              type="button"
              aria-pressed={outfit.is_favorite}
              aria-label="Favourite"
              onClick={() => void toggleFavourite()}
              className={cn(
                "grid size-11 shrink-0 place-content-center rounded-full transition-colors hover:bg-tile",
                focusRing,
              )}
            >
              <Star
                aria-hidden
                className={cn(
                  "size-6",
                  outfit.is_favorite
                    ? "fill-indigo text-indigo"
                    : "text-ink-soft",
                )}
              />
            </button>
          </div>

          {!outfit.complete && (
            <Alert>
              A piece of this outfit was deleted. Edit the outfit to choose
              another.
            </Alert>
          )}

          {present.length > 0 && (
            <MarkWorn
              what={{ outfit_id: outfit.id }}
              wornToday={outfit.last_worn_on === todayIso()}
            />
          )}

          <div className="flex flex-wrap gap-3">
            <Button asChild variant="secondary">
              <Link href={`/outfits/${outfit.id}/edit`}>
                <Pencil aria-hidden />
                Edit
              </Link>
            </Button>
            <Button
              variant="secondary"
              loading={duplicate.isPending}
              onClick={() => void copy()}
            >
              <Copy aria-hidden />
              Duplicate
            </Button>
            <DeleteOutfit outfit={outfit} />
          </div>

          <section
            aria-labelledby="worn-heading"
            className="flex flex-col gap-3"
          >
            <h2 id="worn-heading" className="text-lg font-medium">
              When you wore it
            </h2>
            <WearLogList
              filters={{ outfitId: outfit.id }}
              reference={reference}
              empty={<p className="text-ink-soft">Not worn yet.</p>}
            />
          </section>
        </div>
      </div>
    </div>
  );
}

function DeleteOutfit({ outfit }: { outfit: Outfit }) {
  const router = useRouter();
  const remove = useDeleteOutfit(outfit.id);
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        setError(null);
      }}
    >
      <DialogTrigger asChild>
        <Button variant="quiet">Delete</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete {outfit.display_name}?</DialogTitle>
          <DialogDescription>
            The outfit goes, but not its items. The days you wore it stay in
            your wear log.
          </DialogDescription>
        </DialogHeader>
        {error && <Alert tone="error">{error}</Alert>}
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="secondary">Cancel</Button>
          </DialogClose>
          <Button
            variant="destructive"
            loading={remove.isPending}
            onClick={async () => {
              setError(null);
              try {
                await remove.mutateAsync();
                setOpen(false);
                router.replace("/outfits");
                toast.success("Outfit deleted");
              } catch (failure) {
                setError(problemFrom(failure).message);
              }
            }}
          >
            Delete outfit
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
