import { ReasonList } from "@/components/outfits/reason-list";
import { cn } from "@/lib/utils";

/**
 * The engine's score for the outfit as it stands, moving as pieces change: a bar, the number,
 * and the reasons, as suggestions explain theirs.
 */
export function ScoreMeter({
  score,
  good,
  reasons,
  flat = false,
}: {
  score: number;
  good: boolean;
  reasons: { code: string; kind: "positive" | "caution"; text: string }[];
  // Inside a card already: no panel of its own.
  flat?: boolean;
}) {
  const value = Math.round(score * 100);
  return (
    <div
      aria-live="polite"
      className={cn(
        "flex flex-col gap-2",
        !flat && "rounded-xl bg-surface p-4",
      )}
    >
      <div className="flex items-baseline justify-between gap-3">
        <span className="font-medium">
          {good ? "A good outfit" : "Could be better"}
        </span>
        <span className="text-sm text-ink-soft tabular-nums">
          Score {value} of 100
        </span>
      </div>
      <div
        role="meter"
        aria-label="Outfit score"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={value}
        className="h-2.5 rounded-full bg-tile"
      >
        <span
          className="block h-full rounded-full bg-ink-soft motion-safe:transition-[width]"
          style={{ width: `${value}%` }}
        />
      </div>
      <ReasonList reasons={reasons.slice(0, 3)} />
    </div>
  );
}
