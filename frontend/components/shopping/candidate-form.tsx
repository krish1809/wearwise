"use client";

import { ChevronDown } from "lucide-react";
import { useId, useMemo, useState } from "react";

import { RadioRow } from "@/components/profile/radio-row";
import { toggle } from "@/components/profile/choices";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FilterChip } from "@/components/ui/chip";
import { Field } from "@/components/ui/field";
import { Fieldset } from "@/components/ui/fieldset";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup } from "@/components/ui/radio-group";
import { Select } from "@/components/ui/select";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { ColourChips } from "@/components/wardrobe/item-form";
import { PhotoPicker } from "@/components/wardrobe/photo-picker";
import type { ApiProblem } from "@/lib/api/errors";
import {
  AMOUNT_ERROR,
  MAX_RUPEES,
  paiseToRupeesText,
  rupeesToPaise,
} from "@/lib/money";
import type { Profile, Reference } from "@/lib/profile";
import type { Candidate, NewCandidate } from "@/lib/shopping";
import { type Category, categoriesFor, type PhotoRef } from "@/lib/wardrobe";

type Draft = {
  category_id: string;
  color_primary: string;
  color_hex: string | null;
  name: string;
  brand: string;
  url: string;
  size_label: string;
  price: string;
  target_price: string;
  pattern: string;
  fabric: string;
  fit: string;
  formality: string;
  warmth: string;
  seasons: string[];
  notes: string;
};

/** Details read from a pasted page, for the person to check. */
export type Prefill = {
  name?: string | null;
  brand?: string | null;
  url?: string | null;
  price?: number | null;
  category_id?: string | null;
  color_primary?: string | null;
  fabric?: string | null;
  image_url?: string | null;
};

function draftFrom(candidate: Candidate | undefined, prefill?: Prefill): Draft {
  return {
    category_id: candidate?.category_id ?? prefill?.category_id ?? "",
    color_primary: candidate?.color_primary ?? prefill?.color_primary ?? "",
    color_hex: candidate?.color_hex ?? null,
    name: candidate?.name ?? prefill?.name?.slice(0, 100) ?? "",
    brand: candidate?.brand ?? prefill?.brand ?? "",
    url: candidate?.url ?? prefill?.url ?? "",
    size_label: candidate?.size_label ?? "",
    price: paiseToRupeesText(candidate ? candidate.price : prefill?.price),
    target_price: paiseToRupeesText(candidate?.target_price),
    pattern: candidate?.pattern ?? "solid",
    fabric: candidate?.fabric ?? prefill?.fabric ?? "",
    fit: candidate?.fit ?? "",
    formality: candidate ? String(candidate.formality) : "",
    warmth: candidate ? String(candidate.warmth) : "",
    seasons: candidate?.seasons ?? [],
    notes: candidate?.notes ?? "",
  };
}

const WARMTH = ["None", "Very light", "Light", "Medium", "Warm", "Heavy"];

/**
 * Describe something you're thinking of buying, like an item: a colour and a category are
 * enough for WearWise to say what it would add. The rest sits under "More details".
 */
export function CandidateForm({
  reference,
  categories,
  profile,
  candidate,
  prefill,
  source = "manual",
  saving,
  onSubmit,
}: {
  reference: Reference;
  categories: Category[];
  profile: Profile;
  candidate?: Candidate;
  /** Details read from a pasted page, when adding one. */
  prefill?: Prefill;
  source?: "manual" | "link";
  saving: boolean;
  onSubmit: (body: NewCandidate) => Promise<ApiProblem | null>;
}) {
  const [draft, setDraft] = useState<Draft>(() =>
    draftFrom(candidate, prefill),
  );
  const [imageUrl, setImageUrl] = useState<string | null>(
    candidate?.image_url ?? prefill?.image_url ?? null,
  );
  const [photo, setPhoto] = useState<PhotoRef | null>(candidate?.photo ?? null);
  const [photoChanged, setPhotoChanged] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [more, setMore] = useState(Boolean(candidate || prefill));
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [problem, setProblem] = useState<ApiProblem | null>(null);
  const showAllId = useId();

  const set = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));

  const offered = useMemo(() => {
    const list = categoriesFor(categories, profile.sections, showAll);
    const own = categories.find((c) => c.id === draft.category_id);
    return own && !list.includes(own) ? [own, ...list] : list;
  }, [categories, profile.sections, showAll, draft.category_id]);
  const category = categories.find((c) => c.id === draft.category_id);
  const colourName = reference.color_families.find(
    (c) => c.id === draft.color_primary,
  )?.name;

  async function submit() {
    const found: Record<string, string> = {};
    if (!draft.category_id)
      found.category_id = "Choose what kind of thing it is.";
    if (!draft.color_primary) found.color_primary = "Choose its main colour.";
    const price = rupeesToPaise(draft.price);
    const target = rupeesToPaise(draft.target_price);
    for (const [name, value] of [
      ["price", price],
      ["target_price", target],
    ] as const) {
      if (value !== null && (Number.isNaN(value) || value > MAX_RUPEES * 100)) {
        found[name] = AMOUNT_ERROR;
      }
    }
    const url = draft.url.trim();
    if (url && !/^https?:\/\//i.test(url)) {
      found.url = "Paste a link that starts with https://.";
    }
    setErrors(found);
    setProblem(null);
    if (Object.keys(found).length > 0) return;

    const body: NewCandidate = {
      source,
      image_url: imageUrl,
      category_id: draft.category_id,
      color_primary: draft.color_primary,
      color_hex: draft.color_hex,
      name: draft.name.trim() || null,
      brand: draft.brand.trim() || null,
      url: url || null,
      size_label: draft.size_label.trim() || null,
      price,
      target_price: target,
      pattern: draft.pattern,
      fabric: draft.fabric || null,
      fit: draft.fit || null,
      seasons: draft.seasons,
      notes: draft.notes.trim() || null,
    };
    if (draft.formality) body.formality = Number(draft.formality);
    if (draft.warmth) body.warmth = Number(draft.warmth);
    if (photo && (!candidate || photoChanged)) body.photo_id = photo.id;
    if (candidate && photoChanged && !photo) body.photo_id = null;
    const failure = await onSubmit(body);
    if (failure) setProblem(failure);
  }

  const fieldError = (name: string) => errors[name] ?? problem?.fields[name];

  return (
    <form
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        void submit();
      }}
      className="flex max-w-2xl flex-col gap-7"
    >
      {problem && <Alert tone="error">{problem.message}</Alert>}
      {Object.keys(errors).length > 0 && !problem && (
        <Alert tone="error">Check the highlighted fields.</Alert>
      )}

      <Fieldset
        legend="Photo (optional)"
        hint="A screenshot from the shop is fine."
        error={problem?.fields.photo_id}
      >
        {imageUrl && !photo && (
          <div className="mb-3 flex items-center gap-4">
            <span className="flex size-24 shrink-0 items-center justify-center rounded-lg bg-tile p-1">
              {/* The shop's own picture, from its address; nothing is copied. */}
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={imageUrl}
                alt={draft.name || "The shop's picture"}
                referrerPolicy="no-referrer"
                className="max-h-full max-w-full rounded object-contain"
              />
            </span>
            <div className="flex flex-col items-start gap-1 text-sm text-ink-soft">
              The shop&apos;s picture, shown from its site.
              <Button
                type="button"
                variant="quiet"
                className="-ml-4"
                onClick={() => setImageUrl(null)}
              >
                Don&apos;t use it
              </Button>
            </div>
          </div>
        )}
        <PhotoPicker
          photo={photo}
          alt={
            [draft.name || colourName, category?.name]
              .filter(Boolean)
              .join(", ") || "The piece"
          }
          onUploaded={(uploaded) => {
            setPhoto(uploaded);
            setPhotoChanged(true);
            set("color_hex", uploaded.dominant_hex);
            if (uploaded.suggested_color && !draft.color_primary) {
              set("color_primary", uploaded.suggested_color);
            }
          }}
          onRemove={() => {
            setPhoto(null);
            setPhotoChanged(true);
          }}
        />
      </Fieldset>

      <Fieldset legend="Main colour" error={fieldError("color_primary")}>
        <ColourChips
          colours={reference.color_families}
          value={draft.color_primary}
          onChange={(id) => set("color_primary", id)}
        />
      </Fieldset>

      <div className="flex flex-col gap-3">
        <Field label="Category" error={fieldError("category_id")}>
          {(control) => (
            <Select
              value={draft.category_id}
              onChange={(event) => set("category_id", event.target.value)}
              {...control}
            >
              <option value="">Choose a category</option>
              {reference.category_groups.map((group) => {
                const inGroup = offered.filter((c) => c.group_id === group.id);
                if (inGroup.length === 0) return null;
                return (
                  <optgroup key={group.id} label={group.name}>
                    {inGroup.map((option) => (
                      <option key={option.id} value={option.id}>
                        {option.name}
                      </option>
                    ))}
                  </optgroup>
                );
              })}
            </Select>
          )}
        </Field>
        {profile.sections.length > 0 && (
          <div className="flex min-h-11 items-center gap-3">
            <Switch
              id={showAllId}
              checked={showAll}
              onCheckedChange={setShowAll}
            />
            <Label htmlFor={showAllId} className="text-base font-normal">
              Show all categories
            </Label>
          </div>
        )}
      </div>

      <div className="grid gap-5 sm:grid-cols-2">
        <Field
          label="Price, in rupees (optional)"
          hint="Kept with today's date, since prices change."
          error={fieldError("price")}
        >
          {(control) => (
            <Input
              value={draft.price}
              onChange={(e) => set("price", e.target.value)}
              inputMode="decimal"
              autoComplete="off"
              {...control}
            />
          )}
        </Field>
        <Field label="Link (optional)" error={fieldError("url")}>
          {(control) => (
            <Input
              type="url"
              value={draft.url}
              onChange={(e) => set("url", e.target.value)}
              maxLength={500}
              autoComplete="off"
              placeholder="https://"
              {...control}
            />
          )}
        </Field>
      </div>

      {!more && (
        <Button
          type="button"
          variant="quiet"
          className="-ml-4 self-start"
          onClick={() => setMore(true)}
        >
          <ChevronDown aria-hidden />
          More details
        </Button>
      )}

      {more && (
        <div className="flex flex-col gap-7">
          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Name (optional)" error={fieldError("name")}>
              {(control) => (
                <Input
                  value={draft.name}
                  onChange={(e) => set("name", e.target.value)}
                  maxLength={100}
                  autoComplete="off"
                  {...control}
                />
              )}
            </Field>
            <Field label="Brand (optional)" error={fieldError("brand")}>
              {(control) => (
                <Input
                  value={draft.brand}
                  onChange={(e) => set("brand", e.target.value)}
                  maxLength={100}
                  autoComplete="off"
                  {...control}
                />
              )}
            </Field>
            <Field label="Size (optional)" error={fieldError("size_label")}>
              {(control) => (
                <Input
                  value={draft.size_label}
                  onChange={(e) => set("size_label", e.target.value)}
                  maxLength={20}
                  autoComplete="off"
                  {...control}
                />
              )}
            </Field>
            <Field
              label="Price you'd pay, in rupees (optional)"
              hint="Your own target, for when it's on sale."
              error={fieldError("target_price")}
            >
              {(control) => (
                <Input
                  value={draft.target_price}
                  onChange={(e) => set("target_price", e.target.value)}
                  inputMode="decimal"
                  autoComplete="off"
                  {...control}
                />
              )}
            </Field>
          </div>

          <Fieldset legend="Pattern" error={fieldError("pattern")}>
            <div className="flex flex-wrap gap-2">
              {reference.patterns.map((pattern) => (
                <FilterChip
                  key={pattern.id}
                  selected={draft.pattern === pattern.id}
                  onClick={() => set("pattern", pattern.id)}
                >
                  {pattern.name}
                </FilterChip>
              ))}
            </div>
          </Fieldset>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Fabric (optional)" error={fieldError("fabric")}>
              {(control) => (
                <Select
                  value={draft.fabric}
                  onChange={(e) => set("fabric", e.target.value)}
                  {...control}
                >
                  <option value="">Not set</option>
                  {reference.fabrics.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            <Field label="Fit (optional)" error={fieldError("fit")}>
              {(control) => (
                <Select
                  value={draft.fit}
                  onChange={(e) => set("fit", e.target.value)}
                  {...control}
                >
                  <option value="">Not set</option>
                  {reference.fits.map((f) => (
                    <option key={f.id} value={f.id}>
                      {f.name}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          </div>

          <Fieldset
            legend="Formality"
            hint={
              category
                ? `${category.name} usually: ${reference.formality_levels[category.formality_default - 1]?.name ?? ""}.`
                : undefined
            }
            error={fieldError("formality")}
          >
            <RadioGroup
              value={
                draft.formality || String(category?.formality_default ?? "")
              }
              onValueChange={(value) => set("formality", value)}
            >
              {reference.formality_levels.map((level) => (
                <RadioRow key={level.id} value={level.id} label={level.name} />
              ))}
            </RadioGroup>
          </Fieldset>

          <Field label="Warmth" error={fieldError("warmth")}>
            {(control) => (
              <Select
                value={draft.warmth || String(category?.warmth ?? "")}
                onChange={(e) => set("warmth", e.target.value)}
                className="sm:max-w-xs"
                {...control}
              >
                {!category && <option value="">Choose a category first</option>}
                {WARMTH.map((label, level) => (
                  <option key={level} value={String(level)}>
                    {label}
                  </option>
                ))}
              </Select>
            )}
          </Field>

          <Fieldset
            legend="Seasons"
            hint="Leave all off if it works in any season."
            error={fieldError("seasons")}
          >
            <div className="flex flex-wrap gap-2">
              {reference.seasons.map((season) => (
                <FilterChip
                  key={season.id}
                  selected={draft.seasons.includes(season.id)}
                  onClick={() =>
                    set("seasons", toggle(draft.seasons, season.id))
                  }
                >
                  {season.name}
                </FilterChip>
              ))}
            </div>
          </Fieldset>

          <Field label="Notes (optional)" error={fieldError("notes")}>
            {(control) => (
              <Textarea
                value={draft.notes}
                onChange={(e) => set("notes", e.target.value)}
                maxLength={500}
                {...control}
              />
            )}
          </Field>
        </div>
      )}

      <div className="flex flex-wrap gap-3">
        <Button type="submit" loading={saving}>
          {candidate ? "Save changes" : "Add to shopping list"}
        </Button>
      </div>
    </form>
  );
}
