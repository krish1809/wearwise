"use client";

import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { type ApiProblem, problemFrom } from "@/lib/api/errors";
import type { Reference } from "@/lib/profile";
import { type Category, useCreateCategory } from "@/lib/wardrobe";

type CategoryDialogProps = {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  reference: Reference;
  onCreated?: (category: Category) => void;
};

/** Add a category for something the list doesn't have. */
export function CategoryDialog({
  open,
  onOpenChange,
  reference,
  onCreated,
}: CategoryDialogProps) {
  const create = useCreateCategory();
  const [name, setName] = useState("");
  const [group, setGroup] = useState("");
  const [slot, setSlot] = useState("");
  const [formality, setFormality] = useState("3");
  const [washed, setWashed] = useState("1");
  const [problem, setProblem] = useState<ApiProblem | null>(null);
  const [missing, setMissing] = useState<Record<string, string>>({});

  function reset(next: boolean) {
    onOpenChange(next);
    if (!next) {
      setName("");
      setGroup("");
      setSlot("");
      setFormality("3");
      setWashed("1");
      setProblem(null);
      setMissing({});
    }
  }

  async function submit() {
    const found: Record<string, string> = {};
    if (!name.trim()) found.name = "Enter a name for the category.";
    if (!group) found.group_id = "Choose the kind of thing it is.";
    if (!slot) found.slot = "Choose where it goes in an outfit.";
    setMissing(found);
    setProblem(null);
    if (Object.keys(found).length > 0) return;
    try {
      const category = await create.mutateAsync({
        name: name.trim(),
        group_id: group,
        slot,
        formality_default: Number(formality),
        wears_before_wash: washed === "never" ? null : Number(washed),
      });
      onCreated?.(category);
      reset(false);
    } catch (error) {
      setProblem(problemFrom(error));
    }
  }

  const error = (field: string) => missing[field] ?? problem?.fields[field];

  return (
    <Dialog open={open} onOpenChange={reset}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>New category</DialogTitle>
          <DialogDescription>
            For something the list doesn&apos;t have. Only you see it.
          </DialogDescription>
        </DialogHeader>
        <form
          noValidate
          className="flex flex-col gap-4"
          onSubmit={(event) => {
            event.preventDefault();
            void submit();
          }}
        >
          {problem && Object.keys(problem.fields).length === 0 && (
            <Alert tone="error">{problem.message}</Alert>
          )}
          <Field label="Name" error={error("name")}>
            {(control) => (
              <Input
                value={name}
                onChange={(event) => setName(event.target.value)}
                maxLength={60}
                autoComplete="off"
                {...control}
              />
            )}
          </Field>
          <Field label="Kind of thing" error={error("group_id")}>
            {(control) => (
              <Select
                value={group}
                onChange={(event) => setGroup(event.target.value)}
                {...control}
              >
                <option value="">Choose one</option>
                {reference.category_groups.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <Field
            label="Where it goes in an outfit"
            hint="Outfits have one of each: one top, one pair of shoes, one watch."
            error={error("slot")}
          >
            {(control) => (
              <Select
                value={slot}
                onChange={(event) => setSlot(event.target.value)}
                {...control}
              >
                <option value="">Choose one</option>
                {reference.slots.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Usual formality">
              {(control) => (
                <Select
                  value={formality}
                  onChange={(event) => setFormality(event.target.value)}
                  {...control}
                >
                  {reference.formality_levels.map((level) => (
                    <option key={level.id} value={level.id}>
                      {level.name}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            <Field label="Wash after">
              {(control) => (
                <Select
                  value={washed}
                  onChange={(event) => setWashed(event.target.value)}
                  {...control}
                >
                  {[1, 2, 3, 5, 10].map((wears) => (
                    <option key={wears} value={wears}>
                      {wears === 1 ? "Every wear" : `${wears} wears`}
                    </option>
                  ))}
                  <option value="never">Not on a schedule</option>
                </Select>
              )}
            </Field>
          </div>
          <DialogFooter>
            <DialogClose asChild>
              <Button type="button" variant="secondary">
                Cancel
              </Button>
            </DialogClose>
            <Button type="submit" loading={create.isPending}>
              Add category
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
}
