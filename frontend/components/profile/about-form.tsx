"use client";

import { useState } from "react";

import {
  type SectionFormProps,
  SectionFormFrame,
  useSectionSave,
} from "@/components/profile/section-form";
import { FilterChip } from "@/components/ui/chip";
import { Field } from "@/components/ui/field";
import { Fieldset } from "@/components/ui/fieldset";
import { Input } from "@/components/ui/input";

import { toggle } from "./choices";

export const ABOUT_FIELDS = ["sections", "city"] as const;

/** Which sections the person shops, and their city. */
export function AboutForm({
  profile,
  reference,
  alsoSave,
  onSaved,
  actions,
}: SectionFormProps) {
  const [sections, setSections] = useState(profile.sections);
  const [city, setCity] = useState(profile.city ?? "");
  const { submit, saving, problem, apiError } = useSectionSave({
    alsoSave,
    onSaved,
  });

  return (
    <SectionFormFrame
      onSubmit={() => void submit({ sections, city: city.trim() || null })}
      problem={problem}
      actions={actions({ saving })}
    >
      <Fieldset
        legend="Which sections do you shop?"
        hint="Choose both if you shop both. This only changes which categories come first."
        error={apiError("sections")}
      >
        <div className="flex flex-wrap gap-2">
          {reference.sections.map((section) => (
            <FilterChip
              key={section.id}
              selected={sections.includes(section.id)}
              onClick={() => setSections(toggle(sections, section.id))}
            >
              {section.name}
            </FilterChip>
          ))}
        </div>
      </Fieldset>
      <Field
        label="City"
        hint="WearWise will use it to check the weather when it suggests what to wear."
        error={apiError("city")}
      >
        {(control) => (
          <Input
            value={city}
            onChange={(event) => setCity(event.target.value)}
            autoComplete="address-level2"
            maxLength={100}
            className="sm:max-w-sm"
            {...control}
          />
        )}
      </Field>
    </SectionFormFrame>
  );
}
