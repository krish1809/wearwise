"use client";

import { useParams, useRouter } from "next/navigation";

import { PageLoading } from "@/components/app-shell";
import { OutfitStudio } from "@/components/outfits/outfit-studio";
import { Button } from "@/components/ui/button";
import { ErrorState } from "@/components/ui/error-state";
import { toast } from "@/components/ui/toast";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { useOutfit, useUpdateOutfit } from "@/lib/outfits";

export function EditOutfitContent() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const outfit = useOutfit(id);
  const update = useUpdateOutfit(id);

  if (outfit.isError) {
    return (
      <ErrorState
        title="Couldn't load this outfit"
        action={
          <Button variant="secondary" onClick={() => void outfit.refetch()}>
            Try again
          </Button>
        }
      >
        It may have been deleted, or the connection dropped.
      </ErrorState>
    );
  }
  if (!outfit.data) return <PageLoading />;

  return (
    <div className="flex flex-col gap-6">
      <BackLink href={`/outfits/${id}`}>{outfit.data.display_name}</BackLink>
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        Edit outfit
      </h1>
      <WardrobeData>
        {({ reference }) => (
          <OutfitStudio
            reference={reference}
            outfit={outfit.data}
            saving={update.isPending}
            onSave={async (body) => {
              await update.mutateAsync(body);
              toast.success("Changes saved");
              router.push(`/outfits/${id}`);
            }}
          />
        )}
      </WardrobeData>
    </div>
  );
}
