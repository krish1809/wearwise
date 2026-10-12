"use client";

import { CheckIcon } from "lucide-react";
import { Checkbox as CheckboxPrimitive } from "radix-ui";
import * as React from "react";

import { cn, focusRing } from "@/lib/utils";

function Checkbox({
  className,
  ...props
}: React.ComponentProps<typeof CheckboxPrimitive.Root>) {
  return (
    <CheckboxPrimitive.Root
      data-slot="checkbox"
      className={cn(
        // A 20px box with a 44px touch area around it.
        "relative grid size-5 shrink-0 place-content-center rounded-sm border-2 border-ink-soft bg-surface transition-colors after:absolute after:-inset-3",
        "hover:border-ink data-checked:border-indigo data-checked:bg-indigo data-checked:text-white",
        "disabled:cursor-not-allowed disabled:opacity-50 aria-invalid:border-skip",
        focusRing,
        className,
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator data-slot="checkbox-indicator">
        <CheckIcon aria-hidden className="size-3.5" strokeWidth={3} />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  );
}

export { Checkbox };
