"use client";

import { Search } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { cn, focusRing } from "@/lib/utils";
import { type ItemSummary, useItems } from "@/lib/wardrobe";

type SlotPickerProps = {
  /** The slot being filled, or null when closed. */
  slot: { id: string; name: string } | null;
  statusNames: Map<string, string>;
  familyHex: Map<string, string | null>;
  onClose: () => void;
  onChoose: (item: ItemSummary) => void;
};

/** Choose one of the person's items for a slot, with search. */
export function SlotPicker({
  slot,
  statusNames,
  familyHex,
  onClose,
  onChoose,
}: SlotPickerProps) {
  return (
    <Dialog open={slot !== null} onOpenChange={(open) => !open && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{slot?.name}</DialogTitle>
          <DialogDescription>
            Choose from your wardrobe. Items in the laundry or lent out are
            marked.
          </DialogDescription>
        </DialogHeader>
        {slot && (
          <Choices
            slot={slot.id}
            statusNames={statusNames}
            familyHex={familyHex}
            onChoose={onChoose}
          />
        )}
      </DialogContent>
    </Dialog>
  );
}

function Choices({
  slot,
  statusNames,
  familyHex,
  onChoose,
}: {
  slot: string;
  statusNames: Map<string, string>;
  familyHex: Map<string, string | null>;
  onChoose: (item: ItemSummary) => void;
}) {
  const [q, setQ] = useState("");
  const items = useItems({
    q,
    group: [],
    color: [],
    season: [],
    occasion: [],
    style: [],
    status: [],
    archived: false,
    sort: "newest",
    slot: [slot],
  });
  const shown = (items.data?.pages ?? []).flatMap((page) => page.items);

  return (
    <div className="flex min-h-0 flex-col gap-3">
      <div className="relative">
        <Search
          aria-hidden
          className="pointer-events-none absolute top-1/2 left-3 size-5 -translate-y-1/2 text-ink-soft"
        />
        <Input
          type="search"
          value={q}
          onChange={(event) => setQ(event.target.value)}
          aria-label="Search these items"
          placeholder="Search"
          className="pl-10"
        />
      </div>
      <ul className="grid max-h-[50dvh] grid-cols-3 gap-3 overflow-y-auto p-1">
        {shown.map((item) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => onChoose(item)}
              className={cn("group w-full rounded-lg text-left", focusRing)}
            >
              <span className="flex aspect-3/4 items-center justify-center rounded-lg bg-tile p-2 *:max-h-full *:max-w-full group-hover:bg-line">
                <ItemPhoto
                  photo={item.photo}
                  alt=""
                  hex={item.color_hex ?? familyHex.get(item.color_primary)}
                />
              </span>
              <span className="mt-1 block truncate text-sm font-medium">
                {item.display_name}
              </span>
              {item.status !== "available" && (
                <span className="block truncate text-xs text-ink-soft">
                  {statusNames.get(item.status) ?? item.status}
                </span>
              )}
            </button>
          </li>
        ))}
      </ul>
      {items.data && shown.length === 0 && (
        <p className="text-ink-soft">
          {q
            ? "Nothing matches. Try another word."
            : "Nothing in your wardrobe for this slot yet."}
        </p>
      )}
      {items.hasNextPage && (
        <Button
          variant="quiet"
          loading={items.isFetchingNextPage}
          onClick={() => void items.fetchNextPage()}
        >
          Show more
        </Button>
      )}
    </div>
  );
}
