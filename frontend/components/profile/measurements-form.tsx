"use client";

import { ChevronDown } from "lucide-react";
import { useState } from "react";

import {
  type SectionFormProps,
  SectionFormFrame,
  useSectionSave,
} from "@/components/profile/section-form";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Fieldset } from "@/components/ui/fieldset";
import { Input } from "@/components/ui/input";
import { RadioGroup } from "@/components/ui/radio-group";
import type { Profile } from "@/lib/profile";
import { fromCm, parseNumber, rangeIn, toCm, type Units } from "@/lib/units";

import { RadioRow } from "./radio-row";

export const MEASUREMENTS_FIELDS = ["height_cm", "measurements"] as const;

// The ranges match the backend's (backend/app/api/profile.py), in cm.
const MEASUREMENTS = [
  { key: "height", label: "Height", range: [50, 250], always: true },
  { key: "chest", label: "Chest or bust", range: [50, 200], always: true },
  { key: "waist", label: "Waist", range: [40, 200], always: true },
  { key: "hips", label: "Hips", range: [50, 200], always: false },
  { key: "shoulder", label: "Shoulder width", range: [25, 80], always: false },
  { key: "inseam", label: "Inside leg", range: [40, 120], always: false },
] as const;

type Key = (typeof MEASUREMENTS)[number]["key"];

function stored(profile: Profile, key: Key): number | null {
  if (key === "height") return profile.height_cm;
  return profile.measurements[key] ?? null;
}

function shown(cm: number | null, units: Units): string {
  return cm === null ? "" : String(fromCm(cm, units));
}

/**
 * Body measurements. They are saved in cm. Switching to inches changes only what is shown:
 * a value the person didn't edit is saved exactly as it was, not converted there and back.
 */
export function MeasurementsForm({
  profile,
  alsoSave,
  onSaved,
  actions,
}: SectionFormProps) {
  const [units, setUnits] = useState<Units>(profile.units);
  const [text, setText] = useState(() =>
    Object.fromEntries(
      MEASUREMENTS.map(({ key }) => [key, shown(stored(profile, key), units)]),
    ),
  );
  const [edited, setEdited] = useState<Set<Key>>(() => new Set());
  const [errors, setErrors] = useState<Partial<Record<Key, string>>>({});
  const [showAll, setShowAll] = useState(() =>
    MEASUREMENTS.some(({ key, always }) => !always && stored(profile, key)),
  );
  const { submit, saving, problem, apiError } = useSectionSave({
    alsoSave,
    onSaved,
  });

  function changeUnits(next: Units) {
    setText(
      Object.fromEntries(
        MEASUREMENTS.map(({ key }) => {
          if (!edited.has(key)) return [key, shown(stored(profile, key), next)];
          const value = parseNumber(text[key]);
          if (value === null || Number.isNaN(value)) return [key, text[key]];
          return [key, String(fromCm(toCm(value, units), next))];
        }),
      ),
    );
    setUnits(next);
    setErrors({});
  }

  function save() {
    const found: Partial<Record<Key, string>> = {};
    const cm: Partial<Record<Key, number | null>> = {};
    for (const { key, range } of MEASUREMENTS) {
      if (!edited.has(key)) {
        cm[key] = stored(profile, key);
        continue;
      }
      const value = parseNumber(text[key]);
      const [low, high] = rangeIn(range, units);
      if (
        value !== null &&
        (Number.isNaN(value) || value < low || value > high)
      ) {
        found[key] = `Enter a number between ${low} and ${high} ${units}.`;
      } else {
        cm[key] = value === null ? null : toCm(value, units);
      }
    }
    setErrors(found);
    if (Object.keys(found).length > 0) {
      if (Object.keys(found).some((key) => !isAlwaysShown(key as Key))) {
        setShowAll(true);
      }
      return;
    }
    const { height, ...body } = cm;
    void submit({ units, height_cm: height ?? null, measurements: body });
  }

  const unitName = units === "cm" ? "cm" : "inches";

  return (
    <SectionFormFrame
      onSubmit={save}
      problem={problem}
      hasErrors={Object.keys(errors).length > 0}
      actions={actions({ saving })}
    >
      <p className="text-ink-soft">
        All optional. Measure over light clothing. Your measurements stay
        private to your account, and you can change or delete them any time.
      </p>
      <Fieldset legend="Units">
        <RadioGroup
          value={units}
          onValueChange={(value) => changeUnits(value as Units)}
          className="flex flex-wrap gap-x-6"
        >
          <RadioRow value="cm" label="Centimetres" />
          <RadioRow value="in" label="Inches" />
        </RadioGroup>
      </Fieldset>
      <div className="grid gap-5 sm:grid-cols-2">
        {MEASUREMENTS.filter(({ always }) => always || showAll).map(
          ({ key, label }) => (
            <Field
              key={key}
              label={`${label} (${unitName})`}
              error={
                errors[key] ??
                apiError(key === "height" ? "height_cm" : `measurements.${key}`)
              }
            >
              {(control) => (
                <Input
                  value={text[key]}
                  onChange={(event) => {
                    setText({ ...text, [key]: event.target.value });
                    setEdited(new Set(edited).add(key));
                  }}
                  inputMode="decimal"
                  autoComplete="off"
                  {...control}
                />
              )}
            </Field>
          ),
        )}
      </div>
      {!showAll && (
        <Button
          type="button"
          variant="quiet"
          className="-ml-4 self-start"
          onClick={() => setShowAll(true)}
        >
          <ChevronDown aria-hidden />
          More measurements
        </Button>
      )}
    </SectionFormFrame>
  );
}

function isAlwaysShown(key: Key): boolean {
  return MEASUREMENTS.some((m) => m.key === key && m.always);
}
