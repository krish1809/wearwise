"use client";

import { useRouter } from "next/navigation";

import { CandidateForm } from "@/components/shopping/candidate-form";
import { toast } from "@/components/ui/toast";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { problemFrom } from "@/lib/api/errors";
import { useCreateCandidate } from "@/lib/shopping";

export function NewCandidateContent() {
  const router = useRouter();
  const create = useCreateCandidate();

  return (
    <div className="flex flex-col gap-6">
      <BackLink href="/shopping">Shopping</BackLink>
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Something you&apos;re thinking of buying
        </h1>
        <p className="mt-1 max-w-prose text-ink-soft">
          Describe it like an item in your wardrobe. A colour and a category are
          enough to see what it would add.
        </p>
      </div>
      <WardrobeData>
        {({ reference, categories, profile }) => (
          <CandidateForm
            reference={reference}
            categories={categories}
            profile={profile}
            saving={create.isPending}
            onSubmit={async (body) => {
              try {
                const made = await create.mutateAsync(body);
                toast.success(`${made.display_name} added to your list`);
                router.push(`/shopping/${made.id}`);
                return null;
              } catch (error) {
                return problemFrom(error);
              }
            }}
          />
        )}
      </WardrobeData>
    </div>
  );
}
