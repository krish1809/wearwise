"use client";

import { useRouter } from "next/navigation";

import { OutfitStudio } from "@/components/outfits/outfit-studio";
import { toast } from "@/components/ui/toast";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { useCreateOutfit } from "@/lib/outfits";

export function NewOutfitContent() {
  const router = useRouter();
  const create = useCreateOutfit();

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
            saving={create.isPending}
            onSave={async (body) => {
              const outfit = await create.mutateAsync(body);
              toast.success("Outfit saved");
              router.push(`/outfits/${outfit.id}`);
            }}
          />
        )}
      </WardrobeData>
    </div>
  );
}
