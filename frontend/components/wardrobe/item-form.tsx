"use client";

import { ChevronDown, Plus } from "lucide-react";
import { useId, useMemo, useState } from "react";

import { RadioRow } from "@/components/profile/radio-row";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { FilterChip } from "@/components/ui/chip";
import { Field } from "@/components/ui/field";
import { Fieldset } from "@/components/ui/fieldset";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { RadioGroup } from "@/components/ui/radio-group";
import { Select } from "@/components/ui/select";
import { Swatch } from "@/components/ui/swatch";
import { Switch } from "@/components/ui/switch";
import { Textarea } from "@/components/ui/textarea";
import { CategoryDialog } from "@/components/wardrobe/category-dialog";
import { PhotoPicker } from "@/components/wardrobe/photo-picker";
import type { ApiProblem } from "@/lib/api/errors";
import {
  AMOUNT_ERROR,
  MAX_RUPEES,
  paiseToRupeesText,
  rupeesToPaise,
} from "@/lib/money";
import type { Profile, Reference } from "@/lib/profile";
import { toggle } from "@/components/profile/choices";
import {
  type Category,
  categoriesFor,
  type Item,
  type ItemChanges,
  type NewItem,
  type PhotoRef,
} from "@/lib/wardrobe";

type ItemFormProps = {
  reference: Reference;
  categories: Category[];
  profile: Profile;
  /** The item being edited; left out when adding one. */
  item?: Item;
  saving: boolean;
  /** Called with the whole item when adding, or only what changed when editing. */
  onSubmit: (
    body: NewItem | ItemChanges,
    again: boolean,
  ) => Promise<ApiProblem | null>;
};

type Draft = {
  category_id: string;
  color_primary: string;
  color_secondary: string;
  color_hex: string | null;
  name: string;
  brand: string;
  size_label: string;
  pattern: string;
  fabric: string;
  fit: string;
  // Empty means "the category's default".
  formality: string;
  warmth: string;
  seasons: string[];
  occasion_ids: string[];
  style_tags: string[];
  price: string;
  purchased_on: string;
  status: string;
  wears_before_wash: string;
  notes: string;
};

function draftFrom(item: Item | undefined): Draft {
  return {
    category_id: item?.category_id ?? "",
    color_primary: item?.color_primary ?? "",
    color_secondary: item?.color_secondary ?? "",
    color_hex: item?.color_hex ?? null,
    name: item?.name ?? "",
    brand: item?.brand ?? "",
    size_label: item?.size_label ?? "",
    pattern: item?.pattern ?? "solid",
    fabric: item?.fabric ?? "",
    fit: item?.fit ?? "",
    formality: item ? String(item.formality) : "",
    warmth: item ? String(item.warmth) : "",
    seasons: item?.seasons ?? [],
    occasion_ids: item?.occasion_ids ?? [],
    style_tags: item?.style_tags ?? [],
    price: paiseToRupeesText(item?.price),
    purchased_on: item?.purchased_on ?? "",
    status: item?.status ?? "available",
    wears_before_wash: item
      ? item.wears_before_wash === null
        ? "never"
        : String(item.wears_before_wash)
      : "",
    notes: item?.notes ?? "",
  };
}

const WARMTH = ["None", "Very light", "Light", "Medium", "Warm", "Heavy"];

/**
 * Add or edit an item. A photo, a colour, and a category are enough; the rest starts from the
 * category's defaults and sits under "More details".
 */
export function ItemForm({
  reference,
  categories,
  profile,
  item,
  saving,
  onSubmit,
}: ItemFormProps) {
  const [draft, setDraft] = useState<Draft>(() => draftFrom(item));
  const [photo, setPhoto] = useState<PhotoRef | null>(item?.photo ?? null);
  const [photoChanged, setPhotoChanged] = useState(false);
  const [suggested, setSuggested] = useState<string | null>(null);
  // Once the photo suggests a colour, only it shows until the person asks for the rest.
  const [allColours, setAllColours] = useState(true);
  const [showAll, setShowAll] = useState(false);
  const [more, setMore] = useState(Boolean(item));
  const [categoryOpen, setCategoryOpen] = useState(false);
  const [newTag, setNewTag] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [problem, setProblem] = useState<ApiProblem | null>(null);
  const showAllId = useId();

  const set = <K extends keyof Draft>(key: K, value: Draft[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));

  const offered = useMemo(() => {
    const list = categoriesFor(categories, profile.sections, showAll);
    // An item's own category stays available even if it's outside the sections shopped.
    const own = categories.find((c) => c.id === draft.category_id);
    return own && !list.includes(own) ? [own, ...list] : list;
  }, [categories, profile.sections, showAll, draft.category_id]);
  const category = categories.find((c) => c.id === draft.category_id);
  const colourName = reference.color_families.find(
    (c) => c.id === draft.color_primary,
  )?.name;
  const styleNames = new Map(
    reference.style_profiles.map((s) => [s.id, s.name]),
  );

  function chooseCategory(id: string) {
    set("category_id", id);
  }

  async function submit(again: boolean) {
    const found: Record<string, string> = {};
    if (!draft.category_id)
      found.category_id = "Choose what kind of item it is.";
    if (!draft.color_primary) found.color_primary = "Choose its main colour.";
    const price = rupeesToPaise(draft.price);
    if (price !== null && (Number.isNaN(price) || price > MAX_RUPEES * 100)) {
      found.price = AMOUNT_ERROR;
    }
    setErrors(found);
    setProblem(null);
    if (Object.keys(found).length > 0) return;

    const body: NewItem = {
      category_id: draft.category_id,
      color_primary: draft.color_primary,
      color_secondary: draft.color_secondary || null,
      color_hex: draft.color_hex,
      name: draft.name.trim() || null,
      brand: draft.brand.trim() || null,
      size_label: draft.size_label.trim() || null,
      pattern: draft.pattern,
      fabric: draft.fabric || null,
      fit: draft.fit || null,
      seasons: draft.seasons,
      occasion_ids: draft.occasion_ids,
      style_tags: draft.style_tags,
      price,
      purchased_on: draft.purchased_on || null,
      status: draft.status,
      notes: draft.notes.trim() || null,
    };
    // Left out, these come from the category.
    if (draft.formality) body.formality = Number(draft.formality);
    if (draft.warmth) body.warmth = Number(draft.warmth);
    if (draft.wears_before_wash) {
      body.wears_before_wash =
        draft.wears_before_wash === "never"
          ? null
          : Number(draft.wears_before_wash);
    }
    if (photo && (!item || photoChanged)) body.photo_id = photo.id;
    const sent: NewItem | ItemChanges =
      item && photoChanged && !photo ? { ...body, photo_id: null } : body;

    const failure = await onSubmit(sent, again);
    if (failure) {
      setProblem(failure);
      return;
    }
    if (again) {
      setDraft(draftFrom(undefined));
      setPhoto(null);
      setSuggested(null);
      setAllColours(true);
      setMore(false);
    }
  }

  const fieldError = (name: string) => errors[name] ?? problem?.fields[name];
  const alt = [draft.name || colourName, category?.name]
    .filter(Boolean)
    .join(", ");

  return (
    <form
      noValidate
      onSubmit={(event) => {
        event.preventDefault();
        void submit(false);
      }}
      className="flex max-w-2xl flex-col gap-7"
    >
      {problem && <Alert tone="error">{problem.message}</Alert>}
      {Object.keys(errors).length > 0 && !problem && (
        <Alert tone="error">Check the highlighted fields.</Alert>
      )}

      <Fieldset legend="Photo" error={problem?.fields.photo_id}>
        <PhotoPicker
          photo={photo}
          alt={alt || "The item"}
          onUploaded={(uploaded) => {
            setPhoto(uploaded);
            setPhotoChanged(true);
            set("color_hex", uploaded.dominant_hex);
            if (uploaded.suggested_color && !draft.color_primary) {
              set("color_primary", uploaded.suggested_color);
              setSuggested(uploaded.suggested_color);
              setAllColours(false);
            }
          }}
          onRemove={() => {
            setPhoto(null);
            setPhotoChanged(true);
          }}
        />
      </Fieldset>

      <Fieldset
        legend="Main colour"
        hint={
          suggested && suggested === draft.color_primary
            ? "Suggested from the photo. Change it if it's wrong."
            : undefined
        }
        error={fieldError("color_primary")}
      >
        <ColourChips
          colours={
            allColours
              ? reference.color_families
              : reference.color_families.filter(
                  (c) => c.id === draft.color_primary,
                )
          }
          value={draft.color_primary}
          onChange={(id) => {
            set("color_primary", id);
            if (id !== suggested) setSuggested(null);
          }}
        />
        {!allColours && (
          <Button
            type="button"
            variant="quiet"
            className="mt-2 -ml-4"
            onClick={() => setAllColours(true)}
          >
            Other colours
          </Button>
        )}
      </Fieldset>

      <div className="flex flex-col gap-3">
        <Field label="Category" error={fieldError("category_id")}>
          {(control) => (
            <Select
              value={draft.category_id}
              onChange={(event) => chooseCategory(event.target.value)}
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
        <div className="flex flex-wrap items-center justify-between gap-3">
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
          <Button
            type="button"
            variant="quiet"
            className="-ml-4"
            onClick={() => setCategoryOpen(true)}
          >
            <Plus aria-hidden />
            New category
          </Button>
        </div>
      </div>
      <CategoryDialog
        open={categoryOpen}
        onOpenChange={setCategoryOpen}
        reference={reference}
        onCreated={(created) => chooseCategory(created.id)}
      />

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
            <Field
              label="Name (optional)"
              hint={`Left empty, it's shown as "${[colourName, category?.name.toLowerCase()].filter(Boolean).join(" ") || "colour and category"}".`}
              error={fieldError("name")}
            >
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
            <Field
              label="Size (optional)"
              hint="As written on the label."
              error={fieldError("size_label")}
            >
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
              label="Second colour (optional)"
              error={fieldError("color_secondary")}
            >
              {(control) => (
                <Select
                  value={draft.color_secondary}
                  onChange={(e) => set("color_secondary", e.target.value)}
                  {...control}
                >
                  <option value="">None</option>
                  {reference.color_families.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.name}
                    </option>
                  ))}
                </Select>
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

          <div className="grid gap-5 sm:grid-cols-2">
            <Field label="Warmth" error={fieldError("warmth")}>
              {(control) => (
                <Select
                  value={draft.warmth || String(category?.warmth ?? "")}
                  onChange={(e) => set("warmth", e.target.value)}
                  {...control}
                >
                  {!category && (
                    <option value="">Choose a category first</option>
                  )}
                  {WARMTH.map((label, level) => (
                    <option key={level} value={String(level)}>
                      {label}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
            <Field label="Wash after" error={fieldError("wears_before_wash")}>
              {(control) => (
                <Select
                  value={
                    draft.wears_before_wash ||
                    (category
                      ? category.wears_before_wash === null
                        ? "never"
                        : String(category.wears_before_wash)
                      : "")
                  }
                  onChange={(e) => set("wears_before_wash", e.target.value)}
                  {...control}
                >
                  {!category && (
                    <option value="">Choose a category first</option>
                  )}
                  {[1, 2, 3, 4, 5, 7, 10].map((wears) => (
                    <option key={wears} value={String(wears)}>
                      {wears === 1 ? "Every wear" : `${wears} wears`}
                    </option>
                  ))}
                  <option value="never">Not on a schedule</option>
                </Select>
              )}
            </Field>
          </div>

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

          <Fieldset legend="Occasions" error={fieldError("occasion_ids")}>
            <div className="flex flex-wrap gap-2">
              {reference.occasions.map((occasion) => (
                <FilterChip
                  key={occasion.id}
                  selected={draft.occasion_ids.includes(occasion.id)}
                  onClick={() =>
                    set("occasion_ids", toggle(draft.occasion_ids, occasion.id))
                  }
                >
                  {occasion.name}
                </FilterChip>
              ))}
            </div>
          </Fieldset>

          <Fieldset
            legend="Style tags"
            hint="Styles it belongs to, and any words of your own."
            error={fieldError("style_tags")}
          >
            <div className="flex flex-col gap-3">
              <div className="flex flex-wrap gap-2">
                {reference.style_profiles.map((style) => (
                  <FilterChip
                    key={style.id}
                    selected={draft.style_tags.includes(style.id)}
                    onClick={() =>
                      set("style_tags", toggle(draft.style_tags, style.id))
                    }
                  >
                    {style.name}
                  </FilterChip>
                ))}
                {draft.style_tags
                  .filter((tag) => !styleNames.has(tag))
                  .map((tag) => (
                    <FilterChip
                      key={tag}
                      selected
                      onClick={() =>
                        set("style_tags", toggle(draft.style_tags, tag))
                      }
                    >
                      {tag}
                    </FilterChip>
                  ))}
              </div>
              <div className="flex gap-2 sm:max-w-sm">
                <Input
                  value={newTag}
                  onChange={(e) => setNewTag(e.target.value)}
                  onKeyDown={(event) => {
                    if (event.key === "Enter") {
                      event.preventDefault();
                      addTag();
                    }
                  }}
                  maxLength={30}
                  aria-label="New tag"
                  placeholder="Add your own tag"
                  autoComplete="off"
                />
                <Button type="button" variant="secondary" onClick={addTag}>
                  Add
                </Button>
              </div>
            </div>
          </Fieldset>

          <div className="grid gap-5 sm:grid-cols-2">
            <Field
              label="Price, in rupees (optional)"
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
            <Field
              label="Bought on (optional)"
              error={fieldError("purchased_on")}
            >
              {(control) => (
                <Input
                  type="date"
                  value={draft.purchased_on}
                  onChange={(e) => set("purchased_on", e.target.value)}
                  max={new Date().toISOString().slice(0, 10)}
                  {...control}
                />
              )}
            </Field>
            <Field label="Status" error={fieldError("status")}>
              {(control) => (
                <Select
                  value={draft.status}
                  onChange={(e) => set("status", e.target.value)}
                  {...control}
                >
                  {reference.statuses.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name}
                    </option>
                  ))}
                </Select>
              )}
            </Field>
          </div>

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
          {item ? "Save changes" : "Add item"}
        </Button>
        {!item && (
          <Button
            type="button"
            variant="secondary"
            disabled={saving}
            onClick={() => void submit(true)}
          >
            Add and start another
          </Button>
        )}
      </div>
    </form>
  );

  function addTag() {
    const tag = newTag.trim().replace(/\s+/g, " ").toLowerCase();
    if (tag && !draft.style_tags.includes(tag)) {
      set("style_tags", [...draft.style_tags, tag]);
    }
    setNewTag("");
  }
}

function ColourChips({
  colours,
  value,
  onChange,
}: {
  colours: Reference["color_families"];
  value: string;
  onChange: (id: string) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {colours.map((colour) => (
        <FilterChip
          key={colour.id}
          selected={value === colour.id}
          onClick={() => onChange(colour.id)}
          className="pl-3"
        >
          <Swatch hex={colour.hex} />
          {colour.name}
        </FilterChip>
      ))}
    </div>
  );
}
