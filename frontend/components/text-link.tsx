import Link from "next/link";

import { cn, focusRing } from "@/lib/utils";

/** A link in running text: indigo and underlined, so colour isn't the only sign it's a link. */
export function TextLink({
  className,
  ...props
}: React.ComponentProps<typeof Link>) {
  return (
    <Link
      className={cn(
        "rounded-sm font-medium text-indigo underline underline-offset-4 hover:no-underline",
        focusRing,
        className,
      )}
      {...props}
    />
  );
}
