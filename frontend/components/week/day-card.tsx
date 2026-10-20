"use client";

import {
  Check,
  CloudSun,
  Lock,
  LockOpen,
  Shuffle,
  TriangleAlert,
} from "lucide-react";
import { useId, useState } from "react";

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
import { Select } from "@/components/ui/select";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";
import { problemFrom } from "@/lib/api/errors";
import { dayLabel, isoDay, todayIso } from "@/lib/dates";
import {
  type PlanDay,
  useChangeDay,
  useDayOptions,
  useWearDay,
} from "@/lib/plan";
import type { Reference } from "@/lib/profile";
import { piecesName } from "@/lib/suggestions";
import { cn } from "@/lib/utils";
import { weatherLine, weatherSource } from "@/lib/weather";

type DayCardProps = {
  day: PlanDay;
  start: string;
  reference: Reference;
  /** The occasion this weekday usually has, for the "Usual" option. */
  usualName: string | null;
  slots: { id: string; role: string; position: number }[];
  familyHex: Map<string, string | null>;
};

function heading(iso: string): string {
  const tomorrow = new Date();
  tomorrow.setDate(tomorrow.getDate() + 1);
  if (iso === isoDay(tomorrow)) return "Tomorrow";
  return dayLabel(iso);
}

/** One day of the week: its weather and occasion, the outfit planned, and what to do. */
export function DayCard({
  day,
  start,
  reference,
  usualName,
  slots,
  familyHex,
}: DayCardProps) {
  const titleId = useId();
  const occasionId = useId();
  const change = useChangeDay(start);
  const wear = useWearDay(start);
  const [swapping, setSwapping] = useState(false);
  const planned = day.pieces.length > 0;
  const name = planned ? piecesName(day.pieces) : null;
  const title = heading(day.day);
  const canWear = planned && !day.worn && day.day <= todayIso();
  const pieces = day.pieces.map((piece) => ({
    slot: piece.slot,
    name: piece.item.display_name,
    removed: false,
    item: piece.item,
  }));

  async function save(
    changes: Parameters<typeof change.mutateAsync>[0]["changes"],
  ) {
    try {
      await change.mutateAsync({ day: day.day, changes });
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  return (
    <article
      aria-labelledby={titleId}
      className="flex h-full flex-col gap-3 rounded-xl bg-surface p-4"
    >
      <header className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 id={titleId} className="font-display text-lg font-semibold">
            {title}
          </h2>
          <p className="flex items-center gap-1.5 text-sm text-ink-soft">
            <CloudSun aria-hidden className="size-4 shrink-0" />
            <span>
              {weatherLine(day.weather)}
              <span className="sr-only"> ({weatherSource(day.weather)})</span>
            </span>
          </p>
        </div>
        <Button
          variant="quiet"
          className="px-2"
          aria-pressed={day.locked}
          aria-label={day.locked ? `Unlock ${title}` : `Lock ${title}`}
          disabled={!planned || day.worn || change.isPending}
          onClick={() => void save({ locked: !day.locked })}
        >
          {day.locked ? <Lock aria-hidden /> : <LockOpen aria-hidden />}
          <span className="text-sm">{day.locked ? "Locked" : "Lock"}</span>
        </Button>
      </header>

      {day.events.map((event) => (
        <p key={event.id} className="text-sm font-medium">
          {event.title}
        </p>
      ))}
      <div className="flex flex-col gap-1">
        <label htmlFor={occasionId} className="text-sm text-ink-soft">
          Occasion
        </label>
        <Select
          id={occasionId}
          value={
            day.occasion_source === "chosen" ? (day.occasion_id ?? "") : ""
          }
          disabled={day.worn || change.isPending}
          onChange={(event) =>
            void save({ occasion_id: event.target.value || null })
          }
        >
          <option value="">
            {day.occasion_source === "event"
              ? `From the event: ${reference.occasions.find((o) => o.id === day.occasion_id)?.name ?? ""}`
              : usualName
                ? `Usual: ${usualName}`
                : "Choose an occasion"}
          </option>
          {reference.occasions.map((occasion) => (
            <option key={occasion.id} value={occasion.id}>
              {occasion.name}
            </option>
          ))}
        </Select>
      </div>

      {planned ? (
        <div className="flex flex-col gap-2">
          <OutfitBoard
            pieces={pieces}
            slots={slots}
            familyHex={familyHex}
            size="small"
          />
          <SwatchStrip pieces={pieces} familyHex={familyHex} />
          <p className="font-medium">{name}</p>
          <ReasonList reasons={day.reasons.slice(0, 3)} />
        </div>
      ) : day.missing.length > 0 ? (
        <Alert>{day.missing.join(" ")}</Alert>
      ) : (
        <p className="text-sm text-ink-soft">Not planned yet.</p>
      )}

      {day.outdated && (
        <Flag>Planned for a different occasion. Plan again to update it.</Flag>
      )}
      {day.stale && <Flag>A piece has been deleted or archived since.</Flag>}
      {day.unavailable.length > 0 && !day.worn && (
        <Flag>Not available right now: {day.unavailable.join(", ")}.</Flag>
      )}

      <div className="mt-auto flex flex-wrap gap-2 pt-1">
        {day.worn ? (
          <Button variant="secondary" disabled>
            <Check aria-hidden />
            Worn
          </Button>
        ) : (
          <>
            {canWear && (
              <Button
                loading={wear.isPending}
                onClick={async () => {
                  try {
                    await wear.mutateAsync(day.day);
                    toast.success("Marked as worn");
                  } catch (error) {
                    toast.error(problemFrom(error).message);
                  }
                }}
              >
                I wore this
              </Button>
            )}
            {day.occasion_id && (
              <Button
                variant="secondary"
                aria-label={`Swap the outfit for ${title}`}
                onClick={() => setSwapping(true)}
              >
                <Shuffle aria-hidden />
                Swap
              </Button>
            )}
          </>
        )}
      </div>

      <SwapDialog
        open={swapping}
        onOpenChange={setSwapping}
        title={title}
        day={day.day}
        start={start}
        slots={slots}
        familyHex={familyHex}
        onChoose={async (itemIds) => {
          try {
            await change.mutateAsync({
              day: day.day,
              changes: { item_ids: itemIds },
            });
            setSwapping(false);
            toast.success(
              "Swapped. The day is locked, so planning again keeps it.",
            );
          } catch (error) {
            toast.error(problemFrom(error).message);
          }
        }}
      />
    </article>
  );
}

function Flag({ children }: { children: React.ReactNode }) {
  return (
    <p className="flex items-start gap-2 text-sm text-consider">
      <TriangleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
      <span>{children}</span>
    </p>
  );
}

function SwapDialog({
  open,
  onOpenChange,
  title,
  day,
  start,
  slots,
  familyHex,
  onChoose,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  day: string;
  start: string;
  slots: { id: string; role: string; position: number }[];
  familyHex: Map<string, string | null>;
  onChoose: (itemIds: string[]) => Promise<void>;
}) {
  const options = useDayOptions(start, open ? day : null);
  const [choosing, setChoosing] = useState<string | null>(null);

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] overflow-y-auto sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle>
            Other outfits for{" "}
            {title.toLowerCase() === "today" ? "today" : title}
          </DialogTitle>
          <DialogDescription>
            Each keeps the rest of the week within the rules: nothing past its
            wash, no top twice in three days.
          </DialogDescription>
        </DialogHeader>
        {options.isError ? (
          <Alert tone="error">{problemFrom(options.error).message}</Alert>
        ) : !options.data ? (
          <div aria-busy="true" className="grid gap-6 sm:grid-cols-2">
            {[0, 1].map((key) => (
              <Skeleton key={key} className="aspect-[5/4]" />
            ))}
            <span role="status" className="sr-only">
              Finding outfits
            </span>
          </div>
        ) : options.data.length === 0 ? (
          <Alert>
            Nothing else fits this day without breaking the rest of the week.
          </Alert>
        ) : (
          <ul className="grid gap-x-6 gap-y-8 sm:grid-cols-2">
            {options.data.map((option) => {
              const key = option.item_ids.join();
              const pieces = option.pieces.map((piece) => ({
                slot: piece.slot,
                name: piece.item.display_name,
                removed: false,
                item: piece.item,
              }));
              const name = piecesName(option.pieces);
              return (
                <li key={key} className="flex flex-col gap-3">
                  <OutfitBoard
                    pieces={pieces}
                    slots={slots}
                    familyHex={familyHex}
                    size="small"
                    settle
                  />
                  <SwatchStrip pieces={pieces} familyHex={familyHex} />
                  <p className="font-medium">{name}</p>
                  <ReasonList reasons={option.reasons} />
                  <Button
                    className={cn("self-start")}
                    aria-label={`Wear ${name}`}
                    loading={choosing === key}
                    onClick={async () => {
                      setChoosing(key);
                      await onChoose(option.item_ids);
                      setChoosing(null);
                    }}
                  >
                    Choose this
                  </Button>
                </li>
              );
            })}
          </ul>
        )}
      </DialogContent>
    </Dialog>
  );
}
