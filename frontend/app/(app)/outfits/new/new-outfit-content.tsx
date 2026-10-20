"use client";

import { useRouter } from "next/navigation";

import { OutfitStudio } from "@/components/outfits/outfit-studio";
import { toast } from "@/components/ui/toast";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { useCreateOutfit } from "@/lib/outfits";
import { useSaveSuggestion } from "@/lib/suggestions";

export function NewOutfitContent() {
  const router = useRouter();
  const create = useCreateOutfit();
  const saveSuggestion = useSaveSuggestion();

  return (
    <div className="flex flex-col gap-6">
      <BackLink href="/outfits">Outfits</BackLink>
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        New outfit
      </h1>
      <WardrobeData>
        {({ reference }) => (
          <OutfitStudio
            reference={reference}
            saving={create.isPending || saveSuggestion.isPending}
            onSave={async (body, suggestionId) => {
              // A suggestion saved as it was keeps its engine version and reasons.
              const outfit = suggestionId
                ? await saveSuggestion.mutateAsync({
                    id: suggestionId,
                    body: {
                      name: body.name,
                      occasion_id: body.occasion_id,
                      is_favorite: body.is_favorite,
                    },
                  })
                : await create.mutateAsync(body);
              toast.success("Outfit saved");
              router.push(`/outfits/${outfit.id}`);
            }}
          />
        )}
      </WardrobeData>
    </div>
  );
}
