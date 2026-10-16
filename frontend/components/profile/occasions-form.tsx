"use client";

import { useState } from "react";

import {
  type SectionFormProps,
  SectionFormFrame,
  useSectionSave,
} from "@/components/profile/section-form";
import { FilterChip } from "@/components/ui/chip";
import { Fieldset } from "@/components/ui/fieldset";

import { toggle } from "./choices";

export const OCCASIONS_FIELDS = ["occasion_ids"] as const;

/** The occasions the person dresses for most weeks. */
export function OccasionsForm({
  profile,
  reference,
  alsoSave,
  onSaved,
  actions,
}: SectionFormProps) {
  const [chosen, setChosen] = useState(profile.occasion_ids);
  const { submit, saving, problem, apiError } = useSectionSave({
    alsoSave,
    onSaved,
  });

  return (
    <SectionFormFrame
      onSubmit={() => void submit({ occasion_ids: chosen })}
      problem={problem}
      actions={actions({ saving })}
    >
      <Fieldset
        legend="What do you dress for?"
        hint="Choose any that come up most weeks."
        error={apiError("occasion_ids")}
      >
        <div className="flex flex-wrap gap-2">
          {reference.occasions.map((occasion) => (
            <FilterChip
              key={occasion.id}
              selected={chosen.includes(occasion.id)}
              onClick={() => setChosen(toggle(chosen, occasion.id))}
            >
              {occasion.name}
            </FilterChip>
          ))}
        </div>
      </Fieldset>
    </SectionFormFrame>
  );
}
