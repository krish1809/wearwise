import { CircleCheck, CircleHelp, CircleX } from "lucide-react";

import { cn } from "@/lib/utils";

const VERDICTS = {
  buy: { label: "Buy", icon: CircleCheck, className: "text-buy" },
  consider: { label: "Consider", icon: CircleHelp, className: "text-consider" },
  skip: { label: "Skip", icon: CircleX, className: "text-skip" },
} as const;

type Verdict = keyof typeof VERDICTS;

export function verdictLabel(verdict: string): string {
  return VERDICTS[verdict as Verdict]?.label ?? verdict;
}

/**
 * Buy, Consider, or Skip: always the word with its icon, never colour alone. Without a
 * current verdict, says it hasn't been checked yet.
 */
export function VerdictBadge({
  verdict,
  size = "small",
  className,
}: {
  verdict: string | null | undefined;
  size?: "small" | "large";
  className?: string;
}) {
  const found = verdict ? VERDICTS[verdict as Verdict] : undefined;
  if (!found) {
    return (
      <span className={cn("text-sm text-ink-soft", className)}>
        Not checked yet
      </span>
    );
  }
  const Icon = found.icon;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 font-medium",
        size === "large" ? "text-xl" : "text-sm",
        found.className,
        className,
      )}
    >
      <Icon aria-hidden className={size === "large" ? "size-6" : "size-4"} />
      {found.label}
    </span>
  );
}
