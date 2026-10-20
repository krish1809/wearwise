"use client";

import { useParams, useRouter } from "next/navigation";

import { PageLoading } from "@/components/app-shell";
import { CandidateForm } from "@/components/shopping/candidate-form";
import { ErrorState } from "@/components/ui/error-state";
import { toast } from "@/components/ui/toast";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { problemFrom } from "@/lib/api/errors";
import { useCandidate, useUpdateCandidate } from "@/lib/shopping";

export function EditCandidateContent() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const candidate = useCandidate(id);
  const update = useUpdateCandidate(id);

  return (
    <div className="flex flex-col gap-6">
      <BackLink href={`/shopping/${id}`}>Back</BackLink>
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        Edit
      </h1>
      {candidate.isError ? (
        <ErrorState title="That isn't on your shopping list">
          It may have been deleted.
        </ErrorState>
      ) : !candidate.data ? (
        <PageLoading />
      ) : (
        <WardrobeData>
          {({ reference, categories, profile }) => (
            <CandidateForm
              reference={reference}
              categories={categories}
              profile={profile}
              candidate={candidate.data}
              saving={update.isPending}
              onSubmit={async (body) => {
                try {
                  await update.mutateAsync(body);
                  toast.success("Changes saved");
                  router.push(`/shopping/${id}`);
                  return null;
                } catch (error) {
                  return problemFrom(error);
                }
              }}
            />
          )}
        </WardrobeData>
      )}
    </div>
  );
}
