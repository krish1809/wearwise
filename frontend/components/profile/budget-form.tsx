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
import {
  AMOUNT_ERROR,
  MAX_RUPEES,
  paiseToRupeesText,
  rupeesToPaise,
} from "@/lib/money";

export const BUDGET_FIELDS = ["budget_monthly", "category_budgets"] as const;

const MONTHLY = "monthly";

/** A monthly clothing budget, and what the person usually pays for one piece in each group. */
export function BudgetForm({
  profile,
  reference,
  alsoSave,
  onSaved,
  actions,
}: SectionFormProps) {
  const [monthly, setMonthly] = useState(
    paiseToRupeesText(profile.budget_monthly),
  );
  const [perGroup, setPerGroup] = useState<Record<string, string>>(() =>
    Object.fromEntries(
      reference.category_groups.map((group) => [
        group.id,
        paiseToRupeesText(profile.category_budgets[group.id]),
      ]),
    ),
  );
  const [errors, setErrors] = useState<Record<string, string>>({});
  const { submit, saving, problem, apiError } = useSectionSave({
    alsoSave,
    onSaved,
  });

  function save() {
    const found: Record<string, string> = {};
    const amount = (key: string, text: string): number | null => {
      const paise = rupeesToPaise(text);
      if (paise !== null && (Number.isNaN(paise) || paise > MAX_RUPEES * 100)) {
        found[key] = AMOUNT_ERROR;
      }
      return paise;
    };
    const budget = amount(MONTHLY, monthly);
    const groups: Record<string, number> = {};
    for (const [id, text] of Object.entries(perGroup)) {
      const paise = amount(id, text);
      if (paise !== null && !Number.isNaN(paise)) groups[id] = paise;
    }
    setErrors(found);
    if (Object.keys(found).length > 0) return;
    void submit({ budget_monthly: budget, category_budgets: groups });
  }

  return (
    <SectionFormFrame
      onSubmit={save}
      problem={problem}
      hasErrors={Object.keys(errors).length > 0}
      actions={actions({ saving })}
    >
      <p className="text-ink-soft">
        WearWise will keep shopping suggestions inside these amounts. Leave any
        of them blank if you&apos;d rather not say.
      </p>
      <Field
        label="Monthly clothing budget, in rupees"
        error={errors[MONTHLY] ?? apiError("budget_monthly")}
        className="sm:max-w-xs"
      >
        {(control) => (
          <RupeeInput value={monthly} onChange={setMonthly} control={control} />
        )}
      </Field>
      <Fieldset
        legend="What you usually pay for one piece, in rupees"
        hint="For example, a typical shirt under Tops."
      >
        <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-3">
          {reference.category_groups.map((group) => (
            <Field
              key={group.id}
              label={group.name}
              error={
                errors[group.id] ?? apiError(`category_budgets.${group.id}`)
              }
            >
              {(control) => (
                <RupeeInput
                  value={perGroup[group.id]}
                  onChange={(value) =>
                    setPerGroup({ ...perGroup, [group.id]: value })
                  }
                  control={control}
                />
              )}
            </Field>
          ))}
        </div>
      </Fieldset>
    </SectionFormFrame>
  );
}

function RupeeInput({
  value,
  onChange,
  control,
}: {
  value: string;
  onChange: (value: string) => void;
  control: React.ComponentProps<"input">;
}) {
  return (
    <div className="relative">
      <span
        aria-hidden
        className="pointer-events-none absolute top-1/2 left-3 -translate-y-1/2 text-ink-soft"
      >
        ₹
      </span>
      <Input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        inputMode="decimal"
        autoComplete="off"
        className="pl-7"
        {...control}
      />
    </div>
  );
}
