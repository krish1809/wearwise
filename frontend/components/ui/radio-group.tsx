"use client";

import { RadioGroup as RadioGroupPrimitive } from "radix-ui";
import * as React from "react";

import { cn, focusRing } from "@/lib/utils";

function RadioGroup({
  className,
  ...props
}: React.ComponentProps<typeof RadioGroupPrimitive.Root>) {
  return (
    <RadioGroupPrimitive.Root
      data-slot="radio-group"
      className={cn("grid gap-1", className)}
      {...props}
    />
  );
}

function RadioGroupItem({
  className,
  ...props
}: React.ComponentProps<typeof RadioGroupPrimitive.Item>) {
  return (
    <RadioGroupPrimitive.Item
      data-slot="radio-group-item"
      className={cn(
        // A 20px circle with a 44px touch area around it.
        "relative grid size-5 shrink-0 place-content-center rounded-full border-2 border-ink-soft bg-surface transition-colors after:absolute after:-inset-3",
        "hover:border-ink data-checked:border-indigo",
        "disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-skip",
        focusRing,
        className,
      )}
      {...props}
    >
      <RadioGroupPrimitive.Indicator className="size-2.5 rounded-full bg-indigo" />
    </RadioGroupPrimitive.Item>
  );
}

export { RadioGroup, RadioGroupItem };
