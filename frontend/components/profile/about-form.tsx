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
import { Select } from "@/components/ui/select";
import {
  type ChosenPlace,
  PlaceSearch,
} from "@/components/weather/place-search";
import { MANUAL_WEATHER } from "@/lib/weather";

import { toggle } from "./choices";

export const ABOUT_FIELDS = [
  "sections",
  "city",
  "latitude",
  "longitude",
  "manual_weather",
] as const;

/** Which sections the person shops, their city (for the forecast), and what to assume when
 * there's no forecast. */
export function AboutForm({
  profile,
  reference,
  alsoSave,
  onSaved,
  actions,
}: SectionFormProps) {
  const [sections, setSections] = useState(profile.sections);
  const [place, setPlace] = useState<ChosenPlace | null>(
    profile.city
      ? {
          label: profile.city,
          latitude: profile.latitude,
          longitude: profile.longitude,
        }
      : null,
  );
  const [manual, setManual] = useState(profile.manual_weather ?? "");
  const { submit, saving, problem, apiError } = useSectionSave({
    alsoSave,
    onSaved,
  });

  return (
    <SectionFormFrame
      onSubmit={() =>
        void submit({
          sections,
          city: place?.label ?? null,
          latitude: place?.latitude ?? null,
          longitude: place?.longitude ?? null,
          manual_weather: (manual || null) as
            (typeof MANUAL_WEATHER)[number]["id"] | null,
        })
      }
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
      <PlaceSearch
        label="City"
        hint="For the weather forecast when WearWise suggests what to wear."
        value={place}
        onChange={setPlace}
        error={apiError("city")}
      />
      <Field
        label="When there's no forecast"
        hint="Without a city, or while the weather service is down, plan for this."
        error={apiError("manual_weather")}
      >
        {(control) => (
          <Select
            value={manual}
            onChange={(event) => setManual(event.target.value)}
            className="sm:max-w-xs"
            {...control}
          >
            <option value="">Go by the season</option>
            {MANUAL_WEATHER.map((option) => (
              <option key={option.id} value={option.id}>
                {option.label}
              </option>
            ))}
          </Select>
        )}
      </Field>
    </SectionFormFrame>
  );
}
