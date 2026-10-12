import { cva, type VariantProps } from "class-variance-authority";
import { LoaderCircle } from "lucide-react";
import { Slot } from "radix-ui";
import * as React from "react";

import { cn, focusRing } from "@/lib/utils";

const buttonVariants = cva(
  [
    "inline-flex min-h-11 shrink-0 items-center justify-center gap-2 rounded-lg px-4 text-base font-medium whitespace-nowrap transition-colors select-none",
    "disabled:pointer-events-none disabled:not-aria-busy:opacity-50 aria-busy:cursor-progress",
    "[&_svg]:pointer-events-none [&_svg]:size-5 [&_svg]:shrink-0",
    focusRing,
  ],
  {
    variants: {
      variant: {
        // Ink, not indigo: indigo marks what is selected, and is never a button fill.
        primary: "bg-ink text-white hover:bg-ink/85 active:bg-ink/75",
        secondary:
          "border border-line bg-surface text-ink hover:bg-tile active:bg-line",
        quiet: "text-ink hover:bg-tile active:bg-line",
        destructive: "bg-skip text-white hover:bg-skip/90 active:bg-skip/80",
      },
      size: {
        default: "",
        icon: "w-11 px-0",
      },
    },
    defaultVariants: { variant: "primary", size: "default" },
  },
);

type ButtonProps = React.ComponentProps<"button"> &
  VariantProps<typeof buttonVariants> & {
    /** Give a child element, such as a link, the button's look. */
    asChild?: boolean;
    /** Show a spinner and ignore clicks while the action runs. */
    loading?: boolean;
  };

function Button({
  className,
  variant,
  size,
  asChild = false,
  loading = false,
  disabled,
  children,
  ...props
}: ButtonProps) {
  const classes = cn(buttonVariants({ variant, size }), className);

  if (asChild) {
    return (
      <Slot.Root data-slot="button" className={classes} {...props}>
        {children}
      </Slot.Root>
    );
  }

  return (
    <button
      data-slot="button"
      className={classes}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...props}
    >
      {loading && <LoaderCircle aria-hidden className="animate-spin" />}
      {children}
    </button>
  );
}

export { Button, buttonVariants };
