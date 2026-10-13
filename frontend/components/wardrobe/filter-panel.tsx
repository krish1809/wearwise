"use client";

import { CheckIcon, ChevronDown } from "lucide-react";
import { useId, useState } from "react";

import { TextLink } from "@/components/text-link";
import { FilterChip } from "@/components/ui/chip";
import { Label } from "@/components/ui/label";
import { MULTICOLOUR } from "@/components/ui/swatch";
import { Switch } from "@/components/ui/switch";
import type { ColorFamily, Reference } from "@/lib/profile";
import { cn, focusRing } from "@/lib/utils";
import type { ListFilter, WardrobeFilters } from "@/lib/wardrobe";
import { withToggled } from "@/lib/wardrobe-filters";

type FilterPanelProps = {
  filters: WardrobeFilters;
  reference: Reference;
  onChange: (filters: WardrobeFilters) => void;
};

type ChipGroup = {
  name: ListFilter;
  legend: string;
  options: { id: string; name: string }[];
  open: boolean;
};

/** Every filter. On desktop it's a rail beside the grid; on phones, a bottom sheet. */
export function FilterPanel({
  filters,
  reference,
  onChange,
}: FilterPanelProps) {
  const archivedId = useId();
  const toggle = (name: ListFilter, id: string) =>
    onChange(withToggled(filters, name, id));
  const type: ChipGroup = {
    name: "group",
    legend: "Type",
    options: reference.category_groups,
    open: true,
  };
  const rest: ChipGroup[] = [
    {
      name: "season",
      legend: "Season",
      options: reference.seasons,
      open: false,
    },
    {
      name: "occasion",
      legend: "Occasion",
      options: reference.occasions,
      open: false,
    },
    {
      name: "style",
      legend: "Style",
      options: reference.style_profiles,
      open: false,
    },
    {
      name: "status",
      legend: "Status",
      options: reference.statuses,
      open: false,
    },
  ];

  const chips = (group: ChipGroup) => (
    <Group
      key={group.name}
      legend={group.legend}
      selected={filters[group.name].length}
      defaultOpen={group.open}
    >
      <div className="flex flex-wrap gap-2">
        {group.options.map((option) => (
          <FilterChip
            key={option.id}
            selected={filters[group.name].includes(option.id)}
            onClick={() => toggle(group.name, option.id)}
          >
            {option.name}
          </FilterChip>
        ))}
      </div>
    </Group>
  );

  return (
    <div className="flex flex-col gap-2">
      {chips(type)}
      <Group legend="Colour" selected={filters.color.length} defaultOpen>
        <div className="grid grid-cols-[repeat(auto-fill,minmax(2.5rem,1fr))] gap-2">
          {reference.color_families.map((colour) => (
            <ColourSwatch
              key={colour.id}
              colour={colour}
              selected={filters.color.includes(colour.id)}
              onClick={() => toggle("color", colour.id)}
            />
          ))}
        </div>
      </Group>
      {rest.map(chips)}
      <div className="mt-2 flex min-h-11 items-center gap-3">
        <Switch
          id={archivedId}
          checked={filters.archived}
          onCheckedChange={(archived) => onChange({ ...filters, archived })}
        />
        <Label htmlFor={archivedId} className="text-base font-normal">
          Show archived items instead
        </Label>
      </div>
      <p className="text-sm">
        <TextLink href="/wardrobe/categories">Your categories</TextLink>
      </p>
    </div>
  );
}

/** A filter group that folds away. A group with a choice made starts open. */
function Group({
  legend,
  selected,
  defaultOpen,
  children,
}: {
  legend: string;
  selected: number;
  defaultOpen: boolean;
  children: React.ReactNode;
}) {
  const [open, setOpen] = useState(defaultOpen || selected > 0);
  const regionId = useId();
  return (
    <section className="border-b border-line pb-3">
      <h3>
        <button
          type="button"
          aria-expanded={open}
          aria-controls={regionId}
          onClick={() => setOpen(!open)}
          className={cn(
            "flex min-h-11 w-full items-center justify-between gap-2 rounded-lg text-left text-sm font-medium",
            focusRing,
          )}
        >
          <span>
            {legend}
            {selected > 0 && (
              <span className="ml-2 text-ink-soft tabular-nums">
                {selected}
              </span>
            )}
          </span>
          <ChevronDown
            aria-hidden
            className={cn(
              "size-5 text-ink-soft transition-transform",
              open && "rotate-180",
            )}
          />
        </button>
      </h3>
      <div
        id={regionId}
        role="group"
        aria-label={legend}
        hidden={!open}
        className="pt-1"
      >
        {children}
      </div>
    </section>
  );
}

/** A colour filter as a swatch, named for screen readers and on hover. */
function ColourSwatch({
  colour,
  selected,
  onClick,
}: {
  colour: ColorFamily;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      type="button"
      aria-pressed={selected}
      aria-label={colour.name}
      title={colour.name}
      onClick={onClick}
      className={cn(
        "relative grid aspect-square w-full max-w-11 place-content-center rounded-full border border-line-strong transition-shadow",
        selected && "ring-2 ring-indigo ring-offset-2 ring-offset-surface",
        focusRing,
      )}
      style={{ background: colour.hex ?? MULTICOLOUR }}
    >
      {selected && (
        <CheckIcon
          aria-hidden
          className={cn(
            "size-5",
            isLight(colour.hex) ? "text-ink" : "text-white",
          )}
        />
      )}
    </button>
  );
}

function isLight(hex: string | null): boolean {
  if (!hex) return false;
  const [r, g, b] = [1, 3, 5].map((i) => parseInt(hex.slice(i, i + 2), 16));
  // Perceived brightness, 0 to 255.
  return 0.299 * r + 0.587 * g + 0.114 * b > 150;
}
