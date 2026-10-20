import { Check, TriangleAlert } from "lucide-react";

import { cn } from "@/lib/utils";

type ReasonItem = { code: string; kind: "positive" | "caution"; text: string };

/**
 * Why an outfit works, as the engine said it: positives first, then any cautions. A caution
 * carries an icon and the word in its text, never colour alone.
 */
export function ReasonList({
  reasons,
  className,
}: {
  reasons: ReasonItem[];
  className?: string;
}) {
  if (reasons.length === 0) return null;
  return (
    <ul className={cn("flex flex-col gap-1.5", className)}>
      {reasons.map((reason) => (
        <li key={reason.code} className="flex items-start gap-2 text-sm">
          {reason.kind === "caution" ? (
            <TriangleAlert
              aria-hidden
              className="mt-0.5 size-4 shrink-0 text-consider"
            />
          ) : (
            <Check
              aria-hidden
              className="mt-0.5 size-4 shrink-0 text-ink-soft"
            />
          )}
          <span>
            {reason.kind === "caution" && (
              <span className="sr-only">Worth knowing: </span>
            )}
            {reason.text}
          </span>
        </li>
      ))}
    </ul>
  );
}
