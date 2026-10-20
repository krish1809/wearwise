"use client";

import { CircleCheck, Plus, Star } from "lucide-react";
import { useId, useMemo, useState } from "react";

import { CompleteOutfit } from "@/components/outfits/complete-outfit";
import {
  OutfitBoard,
  SwatchStrip,
  type BoardPiece,
} from "@/components/outfits/outfit-board";
import { SlotPicker } from "@/components/outfits/slot-picker";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { ItemPhoto } from "@/components/wardrobe/item-photo";
import { type ApiProblem, problemFrom } from "@/lib/api/errors";
import { type NewOutfit, type Outfit, useOutfitCheck } from "@/lib/outfits";
import type { Reference } from "@/lib/profile";
import type { PhotoRef } from "@/lib/wardrobe";

/** What the studio needs to know about a chosen item. */
export type ChosenItem = {
  id: string;
  display_name: string;
  slot: string;
  color_primary: string;
  color_hex: string | null;
  photo: PhotoRef | null;
};

type StudioProps = {
  reference: Reference;
  /** The outfit being edited; left out for a new one. */
  outfit?: Outfit;
  saving: boolean;
  /** With a suggestion id when the pieces are exactly a suggestion the person used. */
  onSave: (body: NewOutfit, suggestionId?: string) => Promise<void>;
};

/**
 * Build an outfit slot by slot. The board shows it as it will look; the line under it says
 * what's still needed, checked by the API against the outfit templates.
 */
export function OutfitStudio({
  reference,
  outfit,
  saving,
  onSave,
}: StudioProps) {
  const [chosen, setChosen] = useState<Record<string, ChosenItem>>(() =>
    Object.fromEntries(
      (outfit?.pieces ?? [])
        .filter((piece) => piece.item)
        .map((piece) => [piece.slot, piece.item as ChosenItem]),
    ),
  );
  const removed = (outfit?.pieces ?? []).filter((piece) => piece.removed);
  const [name, setName] = useState(outfit?.name ?? "");
  const [occasion, setOccasion] = useState(outfit?.occasion_id ?? "");
  const [favorite, setFavorite] = useState(outfit?.is_favorite ?? false);
  const [picking, setPicking] = useState<{ id: string; name: string } | null>(
    null,
  );
  const [problem, setProblem] = useState<ApiProblem | null>(null);
  // The suggestion last used to complete the outfit, while its pieces are unchanged.
  const [used, setUsed] = useState<{ id: string; key: string } | null>(null);
  const favoriteId = useId();

  const ids = Object.values(chosen).map((item) => item.id);
  const check = useOutfitCheck(ids);
  const slots = useMemo(
    () => reference.slots.map((slot, position) => ({ ...slot, position })),
    [reference],
  );
  const familyHex = useMemo(
    () => new Map(reference.color_families.map((c) => [c.id, c.hex])),
    [reference],
  );
  const statusNames = useMemo(
    () => new Map(reference.statuses.map((s) => [s.id, s.name])),
    [reference],
  );
  const core = slots.filter((slot) => slot.role === "core");
  const allowed = new Set(check.data?.optional_slots ?? []);
  const touches = slots.filter(
    (slot) => slot.role !== "core" && (allowed.has(slot.id) || chosen[slot.id]),
  );

  const pieces: BoardPiece[] = [
    ...Object.values(chosen).map((item) => ({
      slot: item.slot,
      name: item.display_name,
      removed: false,
      item,
    })),
    ...removed
      .filter((piece) => !chosen[piece.slot])
      .map((piece) => ({
        slot: piece.slot,
        name: piece.name,
        removed: true,
        item: null,
      })),
  ];

  async function save() {
    setProblem(null);
    try {
      await onSave(
        {
          item_ids: ids,
          name: name.trim() || null,
          occasion_id: occasion || null,
          is_favorite: favorite,
        },
        used && used.key === [...ids].sort().join() ? used.id : undefined,
      );
    } catch (error) {
      setProblem(problemFrom(error));
    }
  }

  const status =
    ids.length === 0
      ? "Start with a top or a one-piece."
      : check.data?.complete
        ? `Ready to save: ${check.data.template_name?.toLowerCase() ?? "outfit"}.`
        : check.data?.message;

  return (
    <div className="grid gap-8 lg:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]">
      <div className="flex flex-col gap-3 lg:sticky lg:top-24 lg:self-start">
        <OutfitBoard pieces={pieces} slots={slots} familyHex={familyHex} />
        <SwatchStrip pieces={pieces} familyHex={familyHex} />
        <p role="status" className="flex items-start gap-2 text-ink-soft">
          {check.data?.complete && (
            <CircleCheck
              aria-hidden
              className="mt-0.5 size-5 shrink-0 text-buy"
            />
          )}
          {status}
        </p>
        <CompleteOutfit
          itemIds={ids}
          occasionId={occasion || null}
          slots={slots}
          familyHex={familyHex}
          onUse={(suggestion) => {
            const next = Object.fromEntries(
              suggestion.pieces.map((piece) => [piece.slot, piece.item]),
            );
            setChosen(next);
            setUsed({
              id: suggestion.id,
              key: Object.values(next)
                .map((item) => item.id)
                .sort()
                .join(),
            });
          }}
        />
      </div>

      <form
        noValidate
        className="flex flex-col gap-8"
        onSubmit={(event) => {
          event.preventDefault();
          void save();
        }}
      >
        {problem && <Alert tone="error">{problem.message}</Alert>}

        <section
          aria-labelledby="pieces-heading"
          className="flex flex-col gap-3"
        >
          <h2 id="pieces-heading" className="text-lg font-medium">
            Pieces
          </h2>
          <p className="text-sm text-ink-soft">
            A top, a bottom, and footwear; or a one-piece and footwear. A layer
            is optional.
          </p>
          <ul className="flex flex-col gap-2">
            {core.map((slot) => (
              <SlotRow
                key={slot.id}
                slotName={slot.name}
                item={chosen[slot.id]}
                removedName={
                  removed.find((p) => p.slot === slot.id && !chosen[slot.id])
                    ?.name
                }
                familyHex={familyHex}
                onChoose={() => setPicking({ id: slot.id, name: slot.name })}
                onRemove={() => {
                  const next = { ...chosen };
                  delete next[slot.id];
                  setChosen(next);
                }}
              />
            ))}
          </ul>
        </section>

        <section
          aria-labelledby="touches-heading"
          className="flex flex-col gap-3"
        >
          <h2 id="touches-heading" className="text-lg font-medium">
            Finishing touches
          </h2>
          <p className="text-sm text-ink-soft">
            A belt, a watch, a bag, a fragrance: add any that finish the look.
          </p>
          <ul className="flex flex-col gap-2">
            {touches
              .filter((slot) => chosen[slot.id])
              .map((slot) => (
                <SlotRow
                  key={slot.id}
                  slotName={slot.name}
                  item={chosen[slot.id]}
                  familyHex={familyHex}
                  onChoose={() => setPicking({ id: slot.id, name: slot.name })}
                  onRemove={() => {
                    const next = { ...chosen };
                    delete next[slot.id];
                    setChosen(next);
                  }}
                />
              ))}
          </ul>
          <div className="flex flex-wrap gap-2">
            {touches
              .filter((slot) => !chosen[slot.id])
              .map((slot) => (
                <Button
                  key={slot.id}
                  type="button"
                  variant="secondary"
                  className="min-h-9 rounded-full px-3 text-sm"
                  onClick={() => setPicking({ id: slot.id, name: slot.name })}
                >
                  <Plus aria-hidden className="size-4" />
                  {slot.name}
                </Button>
              ))}
          </div>
        </section>

        <section
          aria-labelledby="details-heading"
          className="flex flex-col gap-5"
        >
          <h2 id="details-heading" className="text-lg font-medium">
            Details
          </h2>
          <Field
            label="Name (optional)"
            hint="Left empty, it's named after its first two pieces."
            error={problem?.fields.name}
          >
            {(control) => (
              <Input
                value={name}
                onChange={(event) => setName(event.target.value)}
                maxLength={100}
                autoComplete="off"
                className="sm:max-w-sm"
                {...control}
              />
            )}
          </Field>
          <Field
            label="Occasion (optional)"
            error={problem?.fields.occasion_id}
          >
            {(control) => (
              <Select
                value={occasion}
                onChange={(event) => setOccasion(event.target.value)}
                className="sm:max-w-sm"
                {...control}
              >
                <option value="">None</option>
                {reference.occasions.map((option) => (
                  <option key={option.id} value={option.id}>
                    {option.name}
                  </option>
                ))}
              </Select>
            )}
          </Field>
          <div className="flex min-h-11 items-center gap-3">
            <Switch
              id={favoriteId}
              checked={favorite}
              onCheckedChange={setFavorite}
            />
            <Label
              htmlFor={favoriteId}
              className="flex items-center gap-2 text-base font-normal"
            >
              <Star aria-hidden className="size-4" />
              Favourite
            </Label>
          </div>
        </section>

        <div>
          <Button type="submit" loading={saving}>
            {outfit ? "Save changes" : "Save outfit"}
          </Button>
        </div>
      </form>

      <SlotPicker
        slot={picking}
        statusNames={statusNames}
        familyHex={familyHex}
        onClose={() => setPicking(null)}
        onChoose={(item) => {
          if (picking) setChosen({ ...chosen, [picking.id]: item });
          setPicking(null);
        }}
      />
    </div>
  );
}

function SlotRow({
  slotName,
  item,
  removedName,
  familyHex,
  onChoose,
  onRemove,
}: {
  slotName: string;
  item: ChosenItem | undefined;
  removedName?: string;
  familyHex: Map<string, string | null>;
  onChoose: () => void;
  onRemove: () => void;
}) {
  return (
    <li className="flex items-center gap-3 rounded-lg bg-surface p-2 pr-3">
      <span className="flex size-14 shrink-0 items-center justify-center rounded-md bg-tile p-1 *:max-h-full *:max-w-full">
        {item && (
          <ItemPhoto
            photo={item.photo}
            alt=""
            hex={item.color_hex ?? familyHex.get(item.color_primary)}
          />
        )}
      </span>
      <span className="min-w-0 flex-1">
        <span className="block text-sm text-ink-soft">{slotName}</span>
        <span className="block truncate font-medium">
          {item
            ? item.display_name
            : removedName
              ? `${removedName} was deleted`
              : "Nothing chosen"}
        </span>
      </span>
      {item && (
        <Button
          type="button"
          variant="quiet"
          className="px-3"
          onClick={onRemove}
          aria-label={`Take ${item.display_name} out`}
        >
          Remove
        </Button>
      )}
      <Button
        type="button"
        variant="secondary"
        className="px-3"
        onClick={onChoose}
        aria-label={`${item ? "Change" : "Choose"} ${slotName.toLowerCase()}`}
      >
        {item ? "Change" : "Choose"}
      </Button>
    </li>
  );
}
