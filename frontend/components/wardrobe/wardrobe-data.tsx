"use client";

import { ChevronLeft } from "lucide-react";
import Link from "next/link";

import { PageLoading } from "@/components/app-shell";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { cn, focusRing } from "@/lib/utils";
import {
  type Profile,
  type Reference,
  useProfile,
  useReference,
} from "@/lib/profile";
import { type Category, useCategories } from "@/lib/wardrobe";

type Loaded = {
  reference: Reference;
  categories: Category[];
  profile: Profile;
};

/** Waits for the lists every wardrobe form needs, with one loading and one error state. */
export function WardrobeData({
  children,
}: {
  children: (data: Loaded) => React.ReactNode;
}) {
  const reference = useReference();
  const categories = useCategories();
  const profile = useProfile();
  const queries = [reference, categories, profile];

  if (queries.some((query) => query.isError)) {
    return (
      <ErrorState
        title="Couldn't reach WearWise"
        action={
          <Button
            variant="secondary"
            onClick={() => queries.forEach((query) => void query.refetch())}
          >
            Try again
          </Button>
        }
      >
        Check your connection and try again.
      </ErrorState>
    );
  }
  if (!reference.data || !categories.data || !profile.data) {
    return <PageLoading />;
  }
  return children({
    reference: reference.data,
    categories: categories.data,
    profile: profile.data,
  });
}

export function BackLink({
  href,
  children,
}: {
  href: string;
  children: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "-ml-1 inline-flex min-h-11 items-center gap-1 self-start rounded-lg pr-2 font-medium text-ink-soft hover:text-ink",
        focusRing,
      )}
    >
      <ChevronLeft aria-hidden className="size-5" />
      {children}
    </Link>
  );
}
