import { CheckIcon, XIcon } from "lucide-react";
import * as React from "react";

import { cn, focusRing } from "@/lib/utils";

type FilterChipProps = React.ComponentProps<"button"> & {
  selected?: boolean;
};

/** A filter that toggles on and off. Selected means indigo, with a tick so colour isn't the only signal. */
function FilterChip({
  selected = false,
  className,
  children,
  ...props
}: FilterChipProps) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      data-slot="filter-chip"
      className={cn(
        // 36px tall, with a 44px touch area.
        "relative inline-flex h-9 shrink-0 items-center gap-1.5 rounded-full border px-4 text-sm font-medium transition-colors after:absolute after:inset-x-0 after:-inset-y-1",
        "disabled:pointer-events-none disabled:opacity-50 [&_svg]:size-4 [&_svg]:shrink-0",
        selected
          ? "border-indigo bg-indigo/10 text-indigo hover:bg-indigo/15 active:bg-indigo/20"
          : "border-line bg-surface text-ink hover:border-ink-soft active:bg-tile",
        focusRing,
        className,
      )}
      {...props}
    >
      {selected && <CheckIcon aria-hidden />}
      {children}
    </button>
  );
}

type RemovableChipProps = {
  label: string;
  onRemove: () => void;
  className?: string;
};

/** An active filter, shown above results; its button removes it. */
function RemovableChip({ label, onRemove, className }: RemovableChipProps) {
  return (
    <span
      data-slot="removable-chip"
      className={cn(
        "inline-flex h-9 shrink-0 items-center gap-1 rounded-full bg-tile pr-1 pl-4 text-sm font-medium text-ink",
        className,
      )}
    >
      {label}
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove ${label}`}
        className={cn(
          "relative grid size-7 place-content-center rounded-full text-ink-soft transition-colors after:absolute after:-inset-2 hover:bg-line hover:text-ink",
          focusRing,
        )}
      >
        <XIcon aria-hidden className="size-4" />
      </button>
    </span>
  );
}

export { FilterChip, RemovableChip };
