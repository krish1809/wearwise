"use client";

import { CheckIcon } from "lucide-react";
import { useState } from "react";

import {
  type SectionFormProps,
  SectionFormFrame,
  useSectionSave,
} from "@/components/profile/section-form";
import { FilterChip } from "@/components/ui/chip";
import { Fieldset } from "@/components/ui/fieldset";
import { Swatch } from "@/components/ui/swatch";
import type { ColorFamily } from "@/lib/profile";
import { cn, focusRing } from "@/lib/utils";

import { toggle } from "./choices";

export const STYLE_FIELDS = [
  "style_profile_ids",
  "preferred_colors",
  "avoided_colors",
] as const;

/** Styles the person likes, and colours they love or avoid. */
export function StyleForm({
  profile,
  reference,
  alsoSave,
  onSaved,
  actions,
}: SectionFormProps) {
  const [styles, setStyles] = useState(profile.style_profile_ids);
  const [loved, setLoved] = useState(profile.preferred_colors);
  const [avoided, setAvoided] = useState(profile.avoided_colors);
  const { submit, saving, problem, apiError } = useSectionSave({
    alsoSave,
    onSaved,
  });
  const hexOf = new Map(reference.color_families.map((c) => [c.id, c.hex]));

  // A colour can be loved or avoided, not both: choosing it in one list takes it out of the other.
  function chooseLoved(id: string) {
    setLoved(toggle(loved, id));
    setAvoided(avoided.filter((existing) => existing !== id));
  }
  function chooseAvoided(id: string) {
    setAvoided(toggle(avoided, id));
    setLoved(loved.filter((existing) => existing !== id));
  }

  return (
    <SectionFormFrame
      onSubmit={() =>
        void submit({
          style_profile_ids: styles,
          preferred_colors: loved,
          avoided_colors: avoided,
        })
      }
      problem={problem}
      actions={actions({ saving })}
    >
      <Fieldset
        legend="Styles you like"
        hint="Choose any number, or none."
        error={apiError("style_profile_ids")}
      >
        <div className="grid gap-3 sm:grid-cols-2">
          {reference.style_profiles.map((style) => {
            const selected = styles.includes(style.id);
            return (
              <button
                key={style.id}
                type="button"
                aria-pressed={selected}
                onClick={() => setStyles(toggle(styles, style.id))}
                className={cn(
                  "flex flex-col gap-2 rounded-lg border bg-surface p-4 text-left transition-colors",
                  selected
                    ? "border-indigo bg-indigo/5"
                    : "border-line hover:border-ink-soft",
                  focusRing,
                )}
              >
                <span className="flex items-center justify-between gap-2 font-medium">
                  {style.name}
                  {selected && (
                    <CheckIcon aria-hidden className="size-5 text-indigo" />
                  )}
                </span>
                <span className="text-sm text-ink-soft">
                  {style.description}
                </span>
                <span className="mt-1 flex gap-1.5">
                  {style.palette.slice(0, 6).map((id) => (
                    <Swatch key={id} hex={hexOf.get(id) ?? null} />
                  ))}
                </span>
              </button>
            );
          })}
        </div>
      </Fieldset>
      <ColourChoices
        legend="Colours you love"
        colours={reference.color_families}
        chosen={loved}
        onChoose={chooseLoved}
        error={apiError("preferred_colors")}
      />
      <ColourChoices
        legend="Colours you avoid"
        colours={reference.color_families}
        chosen={avoided}
        onChoose={chooseAvoided}
        error={apiError("avoided_colors")}
      />
    </SectionFormFrame>
  );
}

function ColourChoices({
  legend,
  colours,
  chosen,
  onChoose,
  error,
}: {
  legend: string;
  colours: ColorFamily[];
  chosen: string[];
  onChoose: (id: string) => void;
  error?: string;
}) {
  return (
    <Fieldset legend={legend} error={error}>
      <div className="flex flex-wrap gap-2">
        {colours.map((colour) => (
          <FilterChip
            key={colour.id}
            selected={chosen.includes(colour.id)}
            onClick={() => onChoose(colour.id)}
            className="pl-3"
          >
            <Swatch hex={colour.hex} />
            {colour.name}
          </FilterChip>
        ))}
      </div>
    </Fieldset>
  );
}
