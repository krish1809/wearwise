"use client";

import { useId } from "react";

import { Label } from "@/components/ui/label";
import { RadioGroupItem } from "@/components/ui/radio-group";

/** One radio with its label; the whole row is a 44px touch target. */
export function RadioRow({ value, label }: { value: string; label: string }) {
  const id = useId();
  return (
    <div className="flex min-h-11 items-center gap-3">
      <RadioGroupItem id={id} value={value} />
      <Label htmlFor={id} className="text-base font-normal">
        {label}
      </Label>
    </div>
  );
}
