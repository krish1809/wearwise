import { CircleAlert } from "lucide-react";
import * as React from "react";

import { cn } from "@/lib/utils";

type FieldsetProps = {
  legend: string;
  /** "group" heads a set of fields with their own labels, so its legend is larger. */
  variant?: "question" | "group";
  hint?: string;
  error?: string;
  className?: string;
  children: React.ReactNode;
};

/**
 * A group of controls that answer one question, such as a set of chips or radios. The legend
 * is read out with each control, like a label.
 */
function Fieldset({
  legend,
  variant = "question",
  hint,
  error,
  className,
  children,
}: FieldsetProps) {
  const id = React.useId();
  const hintId = hint ? `${id}-hint` : undefined;
  const errorId = error ? `${id}-error` : undefined;
  const describedBy = [hintId, errorId].filter(Boolean).join(" ") || undefined;

  return (
    <fieldset
      data-slot="fieldset"
      aria-describedby={describedBy}
      aria-invalid={error ? true : undefined}
      className={cn("flex min-w-0 flex-col gap-2", className)}
    >
      <legend
        className={cn(
          "font-medium text-ink",
          variant === "group" ? "text-base" : "text-sm",
        )}
      >
        {legend}
      </legend>
      {hint && (
        <p id={hintId} className="-mt-0.5 text-sm text-ink-soft">
          {hint}
        </p>
      )}
      <div className="mt-1">{children}</div>
      {error && (
        <p id={errorId} className="flex items-start gap-1.5 text-sm text-skip">
          <CircleAlert aria-hidden className="mt-0.5 size-4 shrink-0" />
          {error}
        </p>
      )}
    </fieldset>
  );
}

export { Fieldset };
