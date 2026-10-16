"use client";

import { useParams, useRouter } from "next/navigation";

import { PageLoading } from "@/components/app-shell";
import { ErrorState } from "@/components/ui/error-state";
import { Button } from "@/components/ui/button";
import { toast } from "@/components/ui/toast";
import { ItemForm } from "@/components/wardrobe/item-form";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { problemFrom } from "@/lib/api/errors";
import { type ItemChanges, useItem, useUpdateItem } from "@/lib/wardrobe";

export function EditItemContent() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const item = useItem(id);
  const update = useUpdateItem(id);

  if (item.isError) {
    return (
      <ErrorState
        title="Couldn't load this item"
        action={
          <Button variant="secondary" onClick={() => void item.refetch()}>
            Try again
          </Button>
        }
      >
        It may have been deleted, or the connection dropped.
      </ErrorState>
    );
  }
  if (!item.data) return <PageLoading />;

  return (
    <div className="flex flex-col gap-6">
      <BackLink href={`/wardrobe/${id}`}>{item.data.display_name}</BackLink>
      <h1 className="font-display text-2xl font-semibold tracking-tight">
        Edit {item.data.display_name}
      </h1>
      <WardrobeData>
        {({ reference, categories, profile }) => (
          <ItemForm
            reference={reference}
            categories={categories}
            profile={profile}
            item={item.data}
            saving={update.isPending}
            onSubmit={async (body) => {
              try {
                await update.mutateAsync(body as ItemChanges);
                toast.success("Changes saved");
                router.push(`/wardrobe/${id}`);
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
