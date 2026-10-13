"use client";

import { NotebookPen, Plus } from "lucide-react";
import { useState } from "react";

import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { EmptyState } from "@/components/ui/empty-state";
import { ErrorState } from "@/components/ui/error-state";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";
import { type ApiProblem, problemFrom } from "@/lib/api/errors";
import {
  type BrandNote,
  useBrandNotes,
  useDeleteBrandNote,
  useSaveBrandNote,
} from "@/lib/brand-notes";

const NOTE_FIELDS = [
  {
    key: "size_notes",
    label: "Size",
    hint: "For example: L in shirts, 32 in jeans.",
  },
  { key: "quality_notes", label: "Quality", hint: undefined },
  { key: "price_notes", label: "Price", hint: undefined },
] as const;

type Draft = {
  brand: string;
  size_notes: string;
  quality_notes: string;
  price_notes: string;
};

const EMPTY: Draft = {
  brand: "",
  size_notes: "",
  quality_notes: "",
  price_notes: "",
};

/** The brand notebook: one note per brand, added, edited, and deleted here. */
export function BrandNotes() {
  const { data: notes, isError, refetch } = useBrandNotes();
  // null: no form open. "new": adding. Otherwise the id of the note being edited.
  const [editing, setEditing] = useState<string | null>(null);

  if (isError) {
    return (
      <ErrorState
        title="Couldn't load your brand notes"
        action={
          <Button variant="secondary" onClick={() => void refetch()}>
            Try again
          </Button>
        }
      >
        Check your connection and try again.
      </ErrorState>
    );
  }
  if (!notes) {
    return (
      <div aria-busy="true" className="flex flex-col gap-3">
        <Skeleton className="h-24" />
        <Skeleton className="h-24" />
        <span role="status" className="sr-only">
          Loading
        </span>
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-4">
      {editing === "new" ? (
        <Card>
          <NoteForm
            title="New brand note"
            initial={EMPTY}
            onDone={() => setEditing(null)}
          />
        </Card>
      ) : (
        <Button
          variant="secondary"
          className="self-start"
          onClick={() => setEditing("new")}
        >
          <Plus aria-hidden />
          Add a brand note
        </Button>
      )}

      {notes.length === 0 && editing !== "new" && (
        <EmptyState icon={<NotebookPen />} title="No brand notes yet">
          Note the sizes that fit you at the brands you buy, such as M at one
          brand and L at another.
        </EmptyState>
      )}

      <ul className="flex flex-col gap-3">
        {notes.map((note) => (
          <li key={note.id}>
            <Card>
              {editing === note.id ? (
                <NoteForm
                  title={`Edit ${note.brand}`}
                  noteId={note.id}
                  initial={draftFrom(note)}
                  onDone={() => setEditing(null)}
                />
              ) : (
                <NoteView note={note} onEdit={() => setEditing(note.id)} />
              )}
            </Card>
          </li>
        ))}
      </ul>
    </div>
  );
}

function draftFrom(note: BrandNote): Draft {
  return {
    brand: note.brand,
    size_notes: note.size_notes ?? "",
    quality_notes: note.quality_notes ?? "",
    price_notes: note.price_notes ?? "",
  };
}

function NoteView({ note, onEdit }: { note: BrandNote; onEdit: () => void }) {
  const written = NOTE_FIELDS.filter(({ key }) => note[key]);
  return (
    <div className="flex flex-col gap-3">
      <h3 className="text-lg font-medium">{note.brand}</h3>
      {written.length > 0 ? (
        <dl className="flex flex-col gap-2">
          {written.map(({ key, label }) => (
            <div
              key={key}
              className="flex flex-col gap-0.5 sm:flex-row sm:gap-6"
            >
              <dt className="w-20 shrink-0 text-ink-soft">{label}</dt>
              <dd className="break-words whitespace-pre-line">{note[key]}</dd>
            </div>
          ))}
        </dl>
      ) : (
        <p className="text-ink-soft">No notes written yet.</p>
      )}
      <div className="flex gap-2">
        <Button variant="secondary" onClick={onEdit}>
          Edit
        </Button>
        <DeleteNote note={note} />
      </div>
    </div>
  );
}

function NoteForm({
  title,
  noteId,
  initial,
  onDone,
}: {
  title: string;
  noteId?: string;
  initial: Draft;
  onDone: () => void;
}) {
  const [draft, setDraft] = useState(initial);
  const [problem, setProblem] = useState<ApiProblem | null>(null);
  const [brandError, setBrandError] = useState<string | null>(null);
  const save = useSaveBrandNote();

  async function submit() {
    setProblem(null);
    const brand = draft.brand.trim();
    if (!brand) {
      setBrandError("Enter the brand's name.");
      return;
    }
    setBrandError(null);
    try {
      await save.mutateAsync({
        id: noteId,
        fields: {
          brand,
          size_notes: draft.size_notes.trim() || null,
          quality_notes: draft.quality_notes.trim() || null,
          price_notes: draft.price_notes.trim() || null,
        },
      });
      toast.success(noteId ? "Brand note saved" : "Brand note added");
      onDone();
    } catch (error) {
      setProblem(problemFrom(error));
    }
  }

  const fieldError = (key: keyof Draft) => problem?.fields[key];
  const otherProblem =
    problem && Object.keys(problem.fields).length === 0 ? problem : null;

  return (
    <form
      noValidate
      aria-label={title}
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
      className="flex flex-col gap-5"
    >
      <h3 className="text-lg font-medium">{title}</h3>
      {otherProblem && <Alert tone="error">{otherProblem.message}</Alert>}
      <Field label="Brand" error={brandError ?? fieldError("brand")}>
        {(control) => (
          <Input
            value={draft.brand}
            onChange={(event) =>
              setDraft({ ...draft, brand: event.target.value })
            }
            maxLength={80}
            autoComplete="off"
            className="sm:max-w-sm"
            {...control}
          />
        )}
      </Field>
      {NOTE_FIELDS.map(({ key, label, hint }) => (
        <Field
          key={key}
          label={`${label} (optional)`}
          hint={hint}
          error={fieldError(key)}
        >
          {(control) => (
            <Input
              value={draft[key]}
              onChange={(event) =>
                setDraft({ ...draft, [key]: event.target.value })
              }
              maxLength={500}
              autoComplete="off"
              {...control}
            />
          )}
        </Field>
      ))}
      <div className="flex flex-wrap gap-3">
        <Button type="submit" loading={save.isPending}>
          {noteId ? "Save note" : "Add note"}
        </Button>
        <Button type="button" variant="quiet" onClick={onDone}>
          Cancel
        </Button>
      </div>
    </form>
  );
}

function DeleteNote({ note }: { note: BrandNote }) {
  const [open, setOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const remove = useDeleteBrandNote();

  async function confirm() {
    setError(null);
    try {
      await remove.mutateAsync(note.id);
      setOpen(false);
      toast.success("Brand note deleted");
    } catch (failure) {
      setError(problemFrom(failure).message);
    }
  }

  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        setOpen(next);
        setError(null);
      }}
    >
      <DialogTrigger asChild>
        <Button variant="quiet">Delete</Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete the note for {note.brand}?</DialogTitle>
          <DialogDescription>
            Its size, quality, and price notes will be removed.
          </DialogDescription>
        </DialogHeader>
        {error && <Alert tone="error">{error}</Alert>}
        <DialogFooter>
          <DialogClose asChild>
            <Button variant="secondary">Cancel</Button>
          </DialogClose>
          <Button
            variant="destructive"
            loading={remove.isPending}
            onClick={() => void confirm()}
          >
            Delete note
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
