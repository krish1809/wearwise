"use client";

import { LogOut, Settings } from "lucide-react";
import Link from "next/link";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn, focusRing } from "@/lib/utils";

/** Up to two letters for the avatar: from the name if there is one, otherwise the email. */
export function initials(name: string | null, email: string): string {
  const words = (name ?? "").trim().split(/\s+/).filter(Boolean);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  if (words.length === 1) return words[0].slice(0, 2).toUpperCase();
  return email.slice(0, 1).toUpperCase();
}

type AvatarMenuProps = {
  name: string | null;
  email: string;
  settingsHref: string;
  onLogOut: () => void;
  /** Start open; the style guide uses this to show the menu. */
  defaultOpen?: boolean;
};

function AvatarMenu({
  name,
  email,
  settingsHref,
  onLogOut,
  defaultOpen,
}: AvatarMenuProps) {
  return (
    <DropdownMenu defaultOpen={defaultOpen} modal={false}>
      <DropdownMenuTrigger
        aria-label="Account menu"
        className={cn(
          "grid size-11 place-content-center rounded-full bg-tile font-medium text-ink transition-colors hover:bg-line data-open:bg-line",
          focusRing,
        )}
      >
        <span aria-hidden>{initials(name, email)}</span>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuLabel>
          {name && <p className="truncate font-medium">{name}</p>}
          <p className="truncate text-sm text-ink-soft">{email}</p>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        <DropdownMenuItem asChild>
          <Link href={settingsHref}>
            <Settings aria-hidden />
            Settings
          </Link>
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={onLogOut}>
          <LogOut aria-hidden />
          Log out
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export { AvatarMenu };
