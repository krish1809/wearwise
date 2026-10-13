"use client";

import { useRouter } from "next/navigation";

import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { ItemForm } from "@/components/wardrobe/item-form";
import { toast } from "@/components/ui/toast";
import { problemFrom } from "@/lib/api/errors";
import { type NewItem, useCreateItem } from "@/lib/wardrobe";

export function NewItemContent() {
  const router = useRouter();
  const create = useCreateItem();

  return (
    <div className="flex flex-col gap-6">
      <BackLink href="/wardrobe">Wardrobe</BackLink>
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        Add an item
      </h1>
      <WardrobeData>
        {({ reference, categories, profile }) => (
          <ItemForm
            reference={reference}
            categories={categories}
            profile={profile}
            saving={create.isPending}
            onSubmit={async (body, again) => {
              try {
                const item = await create.mutateAsync(body as NewItem);
                toast.success(`${item.display_name} added`);
                if (!again) router.push(`/wardrobe/${item.id}`);
                else window.scrollTo({ top: 0 });
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
