"use client";

import { useRef, useState } from "react";

import type { ChosenItem } from "@/components/outfits/outfit-studio";
import { FilterChip } from "@/components/ui/chip";
import { Skeleton } from "@/components/ui/skeleton";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { cn, focusRing } from "@/lib/utils";
import { useItems, type WardrobeFilters } from "@/lib/wardrobe";

/** The item being dragged from the tray, for the board's drop handler. */
export const dragged: { current: ChosenItem | null } = { current: null };

const FILTERS: Omit<WardrobeFilters, "slot"> = {
  q: "",
  group: [],
  color: [],
  season: [],
  occasion: [],
  style: [],
  status: [],
  archived: false,
  sort: "newest",
};

/**
 * Your pieces, a slot at a time. Drag one onto the board, or press it (tap, click, or
 * Enter): both put it in its slot.
 */
export function PieceTray({
  slots,
  chosenIds,
  familyHex,
  onAdd,
  onRemove,
  canDrag = true,
  chosenLabel = "In the outfit",
  hint = "Drag a piece onto the board, or press it to add it.",
}: {
  slots: { id: string; name: string }[];
  chosenIds: string[];
  familyHex: Map<string, string | null>;
  onAdd: (item: ChosenItem) => void;
  // Given, pressing a chosen piece takes it out again.
  onRemove?: (item: ChosenItem) => void;
  canDrag?: boolean;
  chosenLabel?: string;
  hint?: string;
}) {
  const [slot, setSlot] = useState(slots[0]?.id ?? "top");
  const items = useItems({ ...FILTERS, slot: [slot] });
  const list = items.data?.pages.flatMap((page) => page.items) ?? [];
  const strip = useRef<HTMLUListElement>(null);

  return (
    <section aria-labelledby="tray-heading" className="flex flex-col gap-3">
      <div>
        <h2 id="tray-heading" className="text-lg font-medium">
          Your pieces
        </h2>
        <p className="text-sm text-ink-soft">{hint}</p>
      </div>
      <div
        role="group"
        aria-label="Show pieces for"
        className="flex flex-wrap gap-2"
      >
        {slots.map((option) => (
          <FilterChip
            key={option.id}
            selected={slot === option.id}
            onClick={() => setSlot(option.id)}
          >
            {option.name}
          </FilterChip>
        ))}
      </div>
      {items.isLoading ? (
        <Skeleton className="h-28" />
      ) : list.length === 0 ? (
        <p className="text-sm text-ink-soft">
          Nothing of this kind in your wardrobe yet.
        </p>
      ) : (
        <ul ref={strip} className="flex gap-3 overflow-x-auto pb-2">
          {list.map((item) => {
            const piece: ChosenItem = {
              id: item.id,
              display_name: item.display_name,
              slot: item.slot,
              color_primary: item.color_primary,
              color_hex: item.color_hex,
              photo: item.photo,
            };
            const inOutfit = chosenIds.includes(item.id);
            return (
              <li key={item.id} className="shrink-0">
                <button
                  type="button"
                  draggable={canDrag}
                  aria-pressed={inOutfit}
                  aria-label={`${inOutfit ? chosenLabel : "Add"}: ${item.display_name}`}
                  onDragStart={(event) => {
                    dragged.current = piece;
                    event.dataTransfer.effectAllowed = "copy";
                    event.dataTransfer.setData("text/plain", item.id);
                  }}
                  onDragEnd={() => {
                    dragged.current = null;
                  }}
                  onClick={() =>
                    inOutfit && onRemove ? onRemove(piece) : onAdd(piece)
                  }
                  className={cn(
                    "flex w-24 flex-col items-center gap-1 rounded-xl border-2 border-transparent p-1 text-center",
                    canDrag && "cursor-grab active:cursor-grabbing",
                    inOutfit && "border-indigo",
                    focusRing,
                  )}
                >
                  <span className="flex size-20 items-center justify-center rounded-lg bg-tile p-1 *:max-h-full *:max-w-full">
                    <ItemPhoto
                      photo={item.photo}
                      alt=""
                      hex={item.color_hex ?? familyHex.get(item.color_primary)}
                    />
                  </span>
                  <span className="line-clamp-2 text-xs">
                    {item.display_name}
                  </span>
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </section>
  );
}
