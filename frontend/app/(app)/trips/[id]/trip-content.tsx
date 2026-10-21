"use client";

import { CloudSun } from "lucide-react";
import { useParams, useRouter } from "next/navigation";
import { useState } from "react";

import { OutfitBoard, SwatchStrip } from "@/components/outfits/outfit-board";
import { ReasonList } from "@/components/outfits/reason-list";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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
import { ErrorState } from "@/components/ui/error-state";
import { Label } from "@/components/ui/label";
import { toast } from "@/components/ui/toast";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { PageLoading } from "@/components/app-shell";
import { problemFrom } from "@/lib/api/errors";
import { dayLabel } from "@/lib/dates";
import type { Reference } from "@/lib/profile";
import { piecesName } from "@/lib/suggestions";
import {
  type Trip,
  useDeleteTrip,
  useMarkPacked,
  useReplanTrip,
  useTrip,
} from "@/lib/trips";
import { weatherLine } from "@/lib/weather";

export function TripContent() {
  const { id } = useParams<{ id: string }>();
  const trip = useTrip(id);

  if (trip.isError) {
    return (
      <ErrorState
        title="Couldn't load this trip"
        action={
          <Button variant="secondary" onClick={() => void trip.refetch()}>
            Try again
          </Button>
        }
      >
        It may have been deleted. Check your trips.
      </ErrorState>
    );
  }
  if (!trip.data) return <PageLoading />;
  return (
    <WardrobeData>
      {({ reference }) => <TripView trip={trip.data} reference={reference} />}
    </WardrobeData>
  );
}

function TripView({ trip, reference }: { trip: Trip; reference: Reference }) {
  const router = useRouter();
  const packed = useMarkPacked(trip.id);
  const replan = useReplanTrip(trip.id);
  const remove = useDeleteTrip(trip.id);
  const slots = reference.slots.map((slot, position) => ({
    ...slot,
    position,
  }));
  const familyHex = new Map(reference.color_families.map((c) => [c.id, c.hex]));
  const occasions = new Map(reference.occasions.map((o) => [o.id, o.name]));
  const allPacked =
    trip.items.length > 0 && trip.items.every((row) => row.packed);

  async function setPacked(ids: string[], value: boolean) {
    try {
      await packed.mutateAsync({ item_ids: ids, packed: value });
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  return (
    <div className="flex flex-col gap-8">
      <BackLink href="/trips">Trips</BackLink>
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight break-words">
          {trip.destination}
        </h1>
        <p className="mt-1 text-ink-soft">
          {dayLabel(trip.start_date)} to {dayLabel(trip.end_date)} ·{" "}
          {trip.days.length} {trip.days.length === 1 ? "day" : "days"}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-10 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
        <section aria-labelledby="pack-heading" className="flex flex-col gap-4">
          <div>
            <h2 id="pack-heading" className="text-lg font-medium">
              A compact packing list
            </h2>
            <p className="mt-1 text-sm text-ink-soft">
              {trip.items.length} pieces that dress every day below. Packed
              items show as packed in your wardrobe until you unpack them.
            </p>
          </div>
          {trip.items.length > 0 && (
            <Button
              variant="secondary"
              className="self-start"
              loading={packed.isPending}
              onClick={() =>
                void setPacked(
                  trip.items.map((row) => row.item.id),
                  !allPacked,
                )
              }
            >
              {allPacked ? "Unpack all" : "Mark all packed"}
            </Button>
          )}
          <ul className="flex flex-col gap-2">
            {trip.items.map((row) => {
              const checkboxId = `packed-${row.item.id}`;
              return (
                <li
                  key={row.item.id}
                  className="flex items-center gap-3 rounded-lg bg-surface p-2 pr-3"
                >
                  <Checkbox
                    id={checkboxId}
                    checked={row.packed}
                    disabled={packed.isPending}
                    onCheckedChange={(value) =>
                      void setPacked([row.item.id], value === true)
                    }
                    className="ml-2"
                  />
                  <span className="flex size-12 shrink-0 items-center justify-center rounded-md bg-tile p-1 *:max-h-full *:max-w-full">
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
                    <span className="block truncate">
                      {row.item.display_name}
                    </span>
                    <span className="sr-only">
                      {row.packed ? ", packed" : ", not packed"}
                    </span>
                  </Label>
                </li>
              );
            })}
          </ul>
          <div className="rounded-lg bg-surface p-4">
            <h3 className="font-medium">Also pack</h3>
            <ul className="mt-2 list-disc pl-5 text-sm">
              <li>Socks: {trip.basics.socks} pairs</li>
              <li>Underwear: {trip.basics.innerwear}</li>
            </ul>
          </div>
          <div className="flex flex-wrap gap-3">
            <Button
              variant="secondary"
              loading={replan.isPending}
              onClick={async () => {
                try {
                  await replan.mutateAsync();
                  toast.success("Packing list updated");
                } catch (error) {
                  toast.error(problemFrom(error).message);
                }
              }}
            >
              Plan it again
            </Button>
            <DeleteTrip
              deleting={remove.isPending}
              onDelete={async () => {
                try {
                  await remove.mutateAsync();
                  toast.success("Trip deleted");
                  router.push("/trips");
                } catch (error) {
                  toast.error(problemFrom(error).message);
                }
              }}
            />
          </div>
        </section>

        <section aria-labelledby="days-heading" className="flex flex-col gap-4">
          <h2 id="days-heading" className="text-lg font-medium">
            Day by day
          </h2>
          <ol className="grid gap-6 sm:grid-cols-2">
            {trip.days.map((day) => {
              const pieces = day.pieces.map((piece) => ({
                slot: piece.slot,
                name: piece.item.display_name,
                removed: false,
                item: piece.item,
              }));
              return (
                <li
                  key={day.day}
                  className="flex flex-col gap-2 rounded-xl bg-surface p-4"
                >
                  <h3 className="font-display text-lg font-semibold">
                    {dayLabel(day.day)}
                  </h3>
                  <p className="text-sm text-ink-soft">
                    {occasions.get(day.occasion_id) ?? day.occasion_id}
                  </p>
                  <p className="flex items-center gap-1.5 text-sm text-ink-soft">
                    <CloudSun aria-hidden className="size-4 shrink-0" />
                    {weatherLine(day.weather)}
                  </p>
                  {day.pieces.length > 0 ? (
                    <>
                      <OutfitBoard
                        pieces={pieces}
                        slots={slots}
                        familyHex={familyHex}
                        size="small"
                      />
                      <SwatchStrip pieces={pieces} familyHex={familyHex} />
                      <p className="font-medium">{piecesName(day.pieces)}</p>
                      <ReasonList reasons={day.reasons.slice(0, 2)} />
                    </>
                  ) : (
                    <Alert>{day.missing.join(" ")}</Alert>
                  )}
                </li>
              );
            })}
          </ol>
        </section>
      </div>
    </div>
  );
}

function DeleteTrip({
  deleting,
  onDelete,
}: {
  deleting: boolean;
  onDelete: () => Promise<void>;
}) {
  const [open, setOpen] = useState(false);
  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="quiet">Delete trip</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete this trip?</DialogTitle>
          <DialogDescription>
            Anything still marked packed for it goes back to available.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="secondary">Cancel</Button>
          </DialogClose>
          <Button
            variant="destructive"
            loading={deleting}
            onClick={() => void onDelete()}
          >
            Delete trip
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
