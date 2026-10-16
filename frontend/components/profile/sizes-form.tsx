"use client";

import { useState } from "react";

import {
  type SectionFormProps,
  SectionFormFrame,
  useSectionSave,
} from "@/components/profile/section-form";
import { Field } from "@/components/ui/field";
import { Fieldset } from "@/components/ui/fieldset";
import { Input } from "@/components/ui/input";
import { RadioGroup } from "@/components/ui/radio-group";
import { Select } from "@/components/ui/select";
import type { ProfileChanges } from "@/lib/profile";

import { RadioRow } from "./radio-row";

export const SIZES_FIELDS = ["sizes", "fit_preference"] as const;

const GARMENTS = [
  { key: "top", name: "Tops", example: "For example M, or 40" },
  { key: "bottom", name: "Bottoms", example: "For example 32, or M" },
  { key: "shoe", name: "Shoes", example: "For example 9" },
] as const;

type Garment = (typeof GARMENTS)[number]["key"];
type SizeDraft = { label: string; system: string };

const NO_PREFERENCE = "none";

/** Usual sizes, as written on the label, and how the person likes clothes to fit. */
export function SizesForm({
  profile,
  reference,
  alsoSave,
  onSaved,
  actions,
}: SectionFormProps) {
  const [sizes, setSizes] = useState<Record<Garment, SizeDraft>>(() => ({
    top: draftFrom(profile.sizes.top),
    bottom: draftFrom(profile.sizes.bottom),
    shoe: draftFrom(profile.sizes.shoe),
  }));
  const [fit, setFit] = useState(profile.fit_preference ?? NO_PREFERENCE);
  const [errors, setErrors] = useState<Partial<Record<Garment, string>>>({});
  const { submit, saving, problem, apiError } = useSectionSave({
    alsoSave,
    onSaved,
  });

  function save() {
    const found: Partial<Record<Garment, string>> = {};
    const changes: NonNullable<ProfileChanges["sizes"]> = {};
    for (const { key } of GARMENTS) {
      const label = sizes[key].label.trim();
      const system = sizes[key].system || null;
      if (!label && system) {
        found[key] = "Enter a size, or set the sizing system back to Any.";
      } else if (label) {
        changes[key] = { label, system };
      }
    }
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    void submit({
      sizes: changes,
      fit_preference: fit === NO_PREFERENCE ? null : fit,
    });
  }

  return (
    <SectionFormFrame
      onSubmit={save}
      problem={problem}
      hasErrors={Object.keys(errors).length > 0}
      actions={actions({ saving })}
    >
      <p className="text-ink-soft">
        Write sizes as they appear on the label. They vary by brand, so keep any
        differences in Brand notes in Settings.
      </p>
      {GARMENTS.map(({ key, name, example }) => (
        <Fieldset key={key} legend={name} variant="group">
          <div className="grid grid-cols-2 gap-3 sm:gap-4">
            <Field
              label="Size"
              hint={example}
              error={errors[key] ?? apiError(`sizes.${key}.label`)}
            >
              {(control) => (
                <Input
                  value={sizes[key].label}
                  onChange={(event) =>
                    setSizes({
                      ...sizes,
                      [key]: { ...sizes[key], label: event.target.value },
                    })
                  }
                  maxLength={20}
                  autoCapitalize="characters"
                  {...control}
                />
              )}
            </Field>
            <Field
              label="Sizing system"
              error={apiError(`sizes.${key}.system`)}
            >
              {(control) => (
                <Select
                  value={sizes[key].system}
                  onChange={(event) =>
                    setSizes({
                      ...sizes,
                      [key]: { ...sizes[key], system: event.target.value },
                    })
                  }
                  {...control}
                >
                  <option value="">Any</option>
                  {reference.sizing_systems.map((system) => (
                    <option key={system.id} value={system.id}>
                      {system.name}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          </div>
        </Fieldset>
      ))}
      <Fieldset
        legend="How do you like clothes to fit?"
        error={apiError("fit_preference")}
      >
        <RadioGroup value={fit} onValueChange={setFit}>
          {[
            ...reference.fits,
            { id: NO_PREFERENCE, name: "No preference" },
          ].map((option) => (
            <RadioRow key={option.id} value={option.id} label={option.name} />
          ))}
        </RadioGroup>
      </Fieldset>
    </SectionFormFrame>
  );
}

function draftFrom(
  size: { label: string; system?: string | null } | null | undefined,
): SizeDraft {
  return { label: size?.label ?? "", system: size?.system ?? "" };
}
