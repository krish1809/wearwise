"use client";

import { FolderPlus, Plus } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { toast } from "@/components/ui/toast";
import { CategoryDialog } from "@/components/wardrobe/category-dialog";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { problemFrom } from "@/lib/api/errors";
import { type Category, useDeleteCategory } from "@/lib/wardrobe";

/** The person's own categories: add one, or delete one no item uses. */
export function CategoriesContent() {
  const [open, setOpen] = useState(false);

  return (
    <div className="flex max-w-2xl flex-col gap-6">
      <BackLink href="/wardrobe">Wardrobe</BackLink>
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Your categories
        </h1>
        <p className="mt-2 text-ink-soft">
          For things the standard list doesn&apos;t have. Only you see them.
        </p>
      </div>
      <WardrobeData>
        {({ reference, categories }) => {
          const own = categories.filter((category) => category.custom);
          const groupNames = new Map(
            reference.category_groups.map((g) => [g.id, g.name]),
          );
          return (
            <>
              <Button className="self-start" onClick={() => setOpen(true)}>
                <Plus aria-hidden />
                New category
              </Button>
              <CategoryDialog
                open={open}
                onOpenChange={setOpen}
                reference={reference}
                onCreated={(category) =>
                  toast.success(`${category.name} added`)
                }
              />
              {own.length === 0 ? (
                <EmptyState
                  icon={<FolderPlus />}
                  title="No categories of your own yet"
                >
                  Add one when something you own isn&apos;t in the list.
                </EmptyState>
              ) : (
                <ul className="flex flex-col gap-3">
                  {own.map((category) => (
                    <li key={category.id}>
                      <CategoryRow
                        category={category}
                        group={groupNames.get(category.group_id) ?? ""}
                      />
                    </li>
                  ))}
                </ul>
              )}
            </>
          );
        }}
      </WardrobeData>
    </div>
  );
}

function CategoryRow({
  category,
  group,
}: {
  category: Category;
  group: string;
}) {
  const remove = useDeleteCategory();

  async function deleteIt() {
    try {
      await remove.mutateAsync(category.id);
      toast.success(`${category.name} deleted`);
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }

  return (
    <Card className="flex items-center justify-between gap-4">
      <div className="min-w-0">
        <p className="truncate font-medium">{category.name}</p>
        <p className="text-sm text-ink-soft">{group}</p>
      </div>
      <Button
        variant="quiet"
        loading={remove.isPending}
        onClick={() => void deleteIt()}
        aria-label={`Delete ${category.name}`}
      >
        Delete
      </Button>
    </Card>
  );
}
