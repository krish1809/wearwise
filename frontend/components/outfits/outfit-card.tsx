import { Star } from "lucide-react";
import Link from "next/link";

import { OutfitBoard, SwatchStrip } from "@/components/outfits/outfit-board";
import { dayPhrase } from "@/lib/dates";
import type { Outfit } from "@/lib/outfits";
import { cn, focusRing } from "@/lib/utils";

type OutfitCardProps = {
  outfit: Outfit;
  slots: { id: string; role: string; position: number }[];
  familyHex: Map<string, string | null>;
  occasionName?: string;
};

/** A saved outfit in a list: its board, then its name and when it was last worn. */
export function OutfitCard({
  outfit,
  slots,
  familyHex,
  occasionName,
}: OutfitCardProps) {
  return (
    <Link
      href={`/outfits/${outfit.id}`}
      className={cn("group flex flex-col gap-2 rounded-xl", focusRing)}
    >
      <OutfitBoard
        pieces={outfit.pieces}
        slots={slots}
        familyHex={familyHex}
        size="small"
        decorative
        className="transition-colors group-hover:bg-line"
      />
      <SwatchStrip pieces={outfit.pieces} familyHex={familyHex} />
      <div className="min-w-0">
        <p className="flex items-center gap-1.5 font-medium">
          <span className="truncate">{outfit.display_name}</span>
          {outfit.is_favorite && (
            <Star
              aria-label="Favourite"
              className="size-4 shrink-0 fill-indigo text-indigo"
            />
          )}
        </p>
        <p className="truncate text-sm text-ink-soft">
          {[
            occasionName,
            outfit.last_worn_on
              ? `Worn ${outfit.wear_count} ${outfit.wear_count === 1 ? "time" : "times"}, last ${dayPhrase(outfit.last_worn_on)}`
              : "Not worn yet",
            outfit.complete ? null : "A piece was deleted",
          ]
            .filter(Boolean)
            .join(" · ")}
        </p>
      </div>
    </Link>
  );
}
