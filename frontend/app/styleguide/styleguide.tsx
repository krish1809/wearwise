"use client";

import {
  CircleAlert,
  CircleCheck,
  CircleHelp,
  Info,
  Plus,
  Shirt,
  SlidersHorizontal,
} from "lucide-react";
import { useSearchParams } from "next/navigation";
import * as React from "react";

import {
  GarmentShirt,
  GarmentSneaker,
  GarmentTrousers,
} from "@/components/garment-drawings";
import { Alert } from "@/components/ui/alert";
import { AvatarMenu } from "@/components/ui/avatar-menu";
import {
  BottomSheet,
  BottomSheetContent,
  BottomSheetDescription,
  BottomSheetFooter,
  BottomSheetHeader,
  BottomSheetTitle,
  BottomSheetTrigger,
} from "@/components/ui/bottom-sheet";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Checkbox } from "@/components/ui/checkbox";
import { FilterChip, RemovableChip } from "@/components/ui/chip";
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
import { Label } from "@/components/ui/label";
import { LoadMore } from "@/components/ui/load-more";
import { PhotoTile } from "@/components/ui/photo-tile";
import { RadioGroup, RadioGroupItem } from "@/components/ui/radio-group";
import { Select } from "@/components/ui/select";
import { PhotoTileSkeleton, Skeleton } from "@/components/ui/skeleton";
import { Switch } from "@/components/ui/switch";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { toast } from "@/components/ui/toast";
import {
  Tooltip,
  TooltipContent,
  TooltipTrigger,
} from "@/components/ui/tooltip";

const COLOURS = [
  { name: "paper", hex: "#F4F5F3", use: "Page background", swatch: "bg-paper" },
  {
    name: "surface",
    hex: "#FFFFFF",
    use: "Cards, sheets, inputs",
    swatch: "bg-surface",
  },
  {
    name: "tile",
    hex: "#E8EAE7",
    use: "Behind every garment photo",
    swatch: "bg-tile",
  },
  {
    name: "line",
    hex: "#D9DCD8",
    use: "Dividers, card edges",
    swatch: "bg-line",
  },
  {
    name: "line-strong",
    hex: "#858A91",
    use: "Input and select borders",
    swatch: "bg-line-strong",
  },
  {
    name: "ink",
    hex: "#1B1D20",
    use: "Text, primary buttons",
    swatch: "bg-ink",
  },
  {
    name: "ink-soft",
    hex: "#5A5F66",
    use: "Secondary text",
    swatch: "bg-ink-soft",
  },
  {
    name: "indigo",
    hex: "#2C3A82",
    use: "Links, selection, focus, active tab",
    swatch: "bg-indigo",
  },
] as const;

const VERDICTS = [
  { word: "Buy", hex: "#1F7A4D", Icon: CircleCheck, text: "text-buy" },
  { word: "Consider", hex: "#8A5A00", Icon: CircleHelp, text: "text-consider" },
  { word: "Skip", hex: "#B3261E", Icon: CircleAlert, text: "text-skip" },
] as const;

const STATES = [
  { label: "Default", preview: undefined },
  { label: "Hover", preview: "hover" },
  { label: "Focus", preview: "focus" },
  { label: "Pressed", preview: "active" },
] as const;

export function Styleguide() {
  // ?open=dialog|sheet|menu|tooltip|toast opens that overlay, for screenshots.
  const open = useSearchParams().get("open");

  return (
    <main className="mx-auto flex max-w-5xl flex-col gap-16 px-4 py-12 sm:px-6">
      <header className="flex flex-col gap-3">
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Style guide
        </h1>
        <p className="max-w-prose text-ink-soft">
          Every component in every state, from docs/DESIGN_SYSTEM.md. This page
          exists only in development. Add ?open=dialog, sheet, menu, tooltip, or
          toast to the address to see an overlay.
        </p>
      </header>

      <Section
        title="Colour"
        note="The clothes are the colour. The interface stays quiet."
      >
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
          {COLOURS.map((colour) => (
            <div key={colour.name} className="flex flex-col gap-2">
              <div
                className={`h-16 rounded-xl border border-line ${colour.swatch}`}
              />
              <div>
                <p className="font-medium">{colour.name}</p>
                <p className="text-sm text-ink-soft">
                  <span className="tabular-nums">{colour.hex}</span> ·{" "}
                  {colour.use}
                </p>
              </div>
            </div>
          ))}
        </div>
        <div className="flex flex-wrap gap-6">
          {VERDICTS.map(({ word, hex, Icon, text }) => (
            <p
              key={word}
              className={`flex items-center gap-2 font-medium ${text}`}
            >
              <Icon aria-hidden className="size-5" />
              {word}
              <span className="text-sm font-normal text-ink-soft tabular-nums">
                {hex}
              </span>
            </p>
          ))}
        </div>
      </Section>

      <Section
        title="Type"
        note="Bricolage Grotesque for titles and big numbers, Instrument Sans for everything else."
      >
        <div className="flex flex-col gap-4">
          <Sample size="40 display">
            <p className="font-display text-2xl font-semibold tracking-tight">
              Your wardrobe
            </p>
          </Sample>
          <Sample size="28 display">
            <p className="font-display text-xl font-semibold tracking-tight">
              Smart casual, for college
            </p>
          </Sample>
          <Sample size="20">
            <p className="text-lg">Navy and beige are an easy pair</p>
          </Sample>
          <Sample size="16">
            <p>You haven&apos;t worn the loafers in 12 days.</p>
          </Sample>
          <Sample size="14">
            <p className="text-sm text-ink-soft">Cotton · Summer, mild</p>
          </Sample>
          <Sample size="12">
            <p className="text-xs text-ink-soft">Updated 2 hours ago</p>
          </Sample>
          <Sample size="Numbers">
            <p className="tabular-nums">₹1,299 · 14 wears · ₹93 a wear</p>
          </Sample>
        </div>
      </Section>

      <Section title="Buttons">
        {(["primary", "secondary", "quiet", "destructive"] as const).map(
          (variant) => (
            <Row key={variant} label={variant}>
              {STATES.map(({ label, preview }) => (
                <State key={label} label={label}>
                  <Button variant={variant} data-preview={preview}>
                    {variant === "destructive" ? "Delete item" : "Save outfit"}
                  </Button>
                </State>
              ))}
              <State label="Disabled">
                <Button variant={variant} disabled>
                  {variant === "destructive" ? "Delete item" : "Save outfit"}
                </Button>
              </State>
              <State label="Loading">
                <Button variant={variant} loading>
                  {variant === "destructive" ? "Deleting" : "Saving"}
                </Button>
              </State>
            </Row>
          ),
        )}
        <Row label="Icon">
          <State label="Default">
            <Button variant="secondary" size="icon" aria-label="Add item">
              <Plus aria-hidden />
            </Button>
          </State>
          <State label="With icon">
            <Button>
              <Plus aria-hidden />
              Add item
            </Button>
          </State>
        </Row>
      </Section>

      <Section title="Text input">
        <div className="grid gap-6 sm:grid-cols-2">
          <Field label="Email">
            {(control) => (
              <Input type="email" placeholder="you@example.com" {...control} />
            )}
          </Field>
          <Field label="Hover">
            {(control) => (
              <Input
                defaultValue="you@example.com"
                data-preview="hover"
                {...control}
              />
            )}
          </Field>
          <Field label="Focus">
            {(control) => (
              <Input
                defaultValue="you@example.com"
                data-preview="focus"
                {...control}
              />
            )}
          </Field>
          <Field label="Brand" hint="Optional. Helps you search later.">
            {(control) => <Input placeholder="Uniqlo" {...control} />}
          </Field>
          <Field label="Password" error="Use at least 12 characters.">
            {(control) => (
              <Input type="password" defaultValue="short" {...control} />
            )}
          </Field>
          <Field label="Disabled">
            {(control) => (
              <Input disabled defaultValue="you@example.com" {...control} />
            )}
          </Field>
        </div>
      </Section>

      <Section
        title="Select"
        note="A native select, so phones open their own picker. The open list is drawn by the device."
      >
        <div className="grid gap-6 sm:grid-cols-2">
          <FitSelect label="Fit" />
          <FitSelect label="Hover" preview="hover" />
          <FitSelect label="Focus" preview="focus" defaultValue="regular" />
          <FitSelect label="Error" error="Choose a fit." />
          <FitSelect label="Disabled" disabled defaultValue="slim" />
        </div>
      </Section>

      <Section title="Checkbox, radio, switch">
        <div className="grid gap-8 sm:grid-cols-3">
          <fieldset className="flex flex-col gap-1">
            <legend className="mb-2 text-sm font-medium">
              Sections you shop
            </legend>
            <CheckRow label="Menswear" defaultChecked />
            <CheckRow label="Womenswear" />
            <CheckRow label="Focus" preview="focus" />
            <CheckRow label="Disabled" disabled />
          </fieldset>
          <fieldset className="flex flex-col gap-1">
            <legend className="mb-2 text-sm font-medium">Units</legend>
            <RadioGroup defaultValue="cm" aria-label="Units">
              <RadioRow value="cm" label="Centimetres" />
              <RadioRow value="in" label="Inches" />
              <RadioRow value="focus" label="Focus" preview="focus" />
              <RadioRow value="off" label="Disabled" disabled />
            </RadioGroup>
          </fieldset>
          <fieldset className="flex flex-col gap-1">
            <legend className="mb-2 text-sm font-medium">Switches</legend>
            <SwitchRow label="Show all categories" defaultChecked />
            <SwitchRow label="Off" />
            <SwitchRow label="Focus" preview="focus" />
            <SwitchRow label="Disabled" disabled />
          </fieldset>
        </div>
      </Section>

      <Section
        title="Chips"
        note="Filters toggle; active filters sit above results and can be removed."
      >
        <ChipsDemo />
      </Section>

      <Section title="Tabs">
        <Tabs defaultValue="details">
          <TabsList>
            <TabsTrigger value="details">Details</TabsTrigger>
            <TabsTrigger value="wears">Wears</TabsTrigger>
            <TabsTrigger value="goes-with" data-preview="focus">
              Goes with (focus)
            </TabsTrigger>
            <TabsTrigger value="off" disabled>
              Disabled
            </TabsTrigger>
          </TabsList>
          <TabsContent value="details" className="text-ink-soft">
            The selected tab is ink with an indigo underline.
          </TabsContent>
          <TabsContent value="wears" className="text-ink-soft">
            Worn 14 times. Last worn 3 days ago.
          </TabsContent>
          <TabsContent value="goes-with" className="text-ink-soft">
            Goes with 7 things you own.
          </TabsContent>
        </Tabs>
      </Section>

      <Section title="Card">
        <Card className="max-w-md">
          <CardTitle>This week</CardTitle>
          <CardDescription className="mt-1">
            Cards are white on the paper background. Depth comes from the
            colours, not from shadows.
          </CardDescription>
        </Card>
      </Section>

      <Section
        title="Photo tiles"
        note="3:4, garment padded on the tile colour, one line of detail. Loading uses the same shape."
      >
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-5">
          <PhotoTile
            name="Navy oxford shirt"
            detail="Navy · Shirt"
            href="#tiles"
          >
            <GarmentShirt />
          </PhotoTile>
          <PhotoTile
            name="Beige chinos"
            detail="Beige · Trousers"
            href="#tiles"
            className="[&>div:first-child]:bg-line"
          >
            <GarmentTrousers />
          </PhotoTile>
          <PhotoTile
            name="White sneakers (focus)"
            detail="White · Sneakers"
            href="#tiles"
            data-preview="focus"
          >
            <GarmentSneaker />
          </PhotoTile>
          <PhotoTileSkeleton />
          <PhotoTileSkeleton />
        </div>
        <p className="text-sm text-ink-soft">
          The second tile shows the hover colour. Sample drawings, not real
          items.
        </p>
      </Section>

      <Section title="Dialog">
        <Dialog defaultOpen={open === "dialog"}>
          <div className="flex">
            <DialogTrigger asChild>
              <Button variant="secondary">Open dialog</Button>
            </DialogTrigger>
          </div>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Delete this item?</DialogTitle>
              <DialogDescription>
                It will be removed from your wardrobe and from saved outfits.
                This can&apos;t be undone.
              </DialogDescription>
            </DialogHeader>
            <DialogFooter>
              <DialogClose asChild>
                <Button variant="secondary">Cancel</Button>
              </DialogClose>
              <DialogClose asChild>
                <Button variant="destructive">Delete item</Button>
              </DialogClose>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </Section>

      <Section
        title="Bottom sheet"
        note="Phones get a sheet where desktop has a side rail."
      >
        <BottomSheet defaultOpen={open === "sheet"}>
          <div className="flex">
            <BottomSheetTrigger asChild>
              <Button variant="secondary">
                <SlidersHorizontal aria-hidden />
                Filters
              </Button>
            </BottomSheetTrigger>
          </div>
          <BottomSheetContent>
            <BottomSheetHeader>
              <BottomSheetTitle>Filters</BottomSheetTitle>
              <BottomSheetDescription>
                Show items that match all of these.
              </BottomSheetDescription>
            </BottomSheetHeader>
            <div className="flex flex-wrap gap-2 px-4 py-4">
              <FilterChip selected>Summer</FilterChip>
              <FilterChip>Monsoon</FilterChip>
              <FilterChip>Winter</FilterChip>
              <FilterChip selected>Cotton</FilterChip>
            </div>
            <BottomSheetFooter>
              <Button>Show 24 items</Button>
            </BottomSheetFooter>
          </BottomSheetContent>
        </BottomSheet>
      </Section>

      <Section
        title="Toast"
        note="System messages: a white card with a coloured icon. The text says what happened."
      >
        <ToastDemo showOnLoad={open === "toast"} />
      </Section>

      <Section title="Tooltip">
        <Tooltip defaultOpen={open === "tooltip"}>
          <TooltipTrigger asChild>
            <Button
              variant="quiet"
              size="icon"
              aria-label="About wears before wash"
            >
              <Info aria-hidden />
            </Button>
          </TooltipTrigger>
          <TooltipContent>
            How many times you wear it before it needs a wash.
          </TooltipContent>
        </Tooltip>
      </Section>

      <Section title="Skeleton">
        <div className="flex max-w-md flex-col gap-2">
          <Skeleton className="h-7 w-1/2" />
          <Skeleton className="h-4 w-full" />
          <Skeleton className="h-4 w-5/6" />
        </div>
      </Section>

      <Section
        title="Alert"
        note="A message about a whole form or page. The icon carries the tone."
      >
        <div className="flex max-w-md flex-col gap-3">
          <Alert>Your session has ended. Log in again.</Alert>
          <Alert tone="error">
            That email and password don&apos;t match an account. Check them and
            try again.
          </Alert>
        </div>
      </Section>

      <Section title="Empty and error states">
        <div className="grid gap-6 lg:grid-cols-2">
          <EmptyState
            icon={<Shirt />}
            title="Your wardrobe is empty"
            action={
              <Button>
                <Plus aria-hidden />
                Add item
              </Button>
            }
          >
            Add your first item. A photo and a colour are enough.
          </EmptyState>
          <ErrorState
            title="Couldn't load your items"
            action={<Button variant="secondary">Try again</Button>}
          >
            Check your connection and try again.
          </ErrorState>
        </div>
      </Section>

      <Section title="Load more">
        <LoadMoreDemo />
      </Section>

      <Section title="Avatar menu">
        <div className="flex">
          <AvatarMenu
            name="Sam Lee"
            email="sam@example.com"
            settingsHref="#avatar"
            onLogOut={() => toast("Logged out")}
            defaultOpen={open === "menu"}
          />
        </div>
      </Section>
    </main>
  );
}

function Section({
  title,
  note,
  children,
}: {
  title: string;
  note?: string;
  children: React.ReactNode;
}) {
  return (
    <section className="flex flex-col gap-6">
      <div className="flex flex-col gap-1 border-b border-line pb-3">
        <h2 className="font-display text-xl font-semibold tracking-tight">
          {title}
        </h2>
        {note && <p className="text-ink-soft">{note}</p>}
      </div>
      {children}
    </section>
  );
}

function Row({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-3">
      <p className="text-sm font-medium text-ink-soft first-letter:uppercase">
        {label}
      </p>
      <div className="flex flex-wrap items-start gap-4">{children}</div>
    </div>
  );
}

function State({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col items-start gap-2">
      {children}
      <span className="text-xs text-ink-soft">{label}</span>
    </div>
  );
}

function Sample({
  size,
  children,
}: {
  size: string;
  children: React.ReactNode;
}) {
  return (
    <div className="flex flex-col gap-1 sm:flex-row sm:items-baseline sm:gap-6">
      <span className="w-28 shrink-0 text-xs text-ink-soft">{size}</span>
      {children}
    </div>
  );
}

function FitSelect({
  label,
  preview,
  error,
  disabled,
  defaultValue,
}: {
  label: string;
  preview?: string;
  error?: string;
  disabled?: boolean;
  defaultValue?: string;
}) {
  return (
    <Field label={label} error={error}>
      {(control) => (
        <Select
          defaultValue={defaultValue ?? ""}
          disabled={disabled}
          data-preview={preview}
          {...control}
        >
          <option value="">Choose a fit</option>
          <option value="slim">Slim</option>
          <option value="regular">Regular</option>
          <option value="relaxed">Relaxed</option>
          <option value="oversized">Oversized</option>
        </Select>
      )}
    </Field>
  );
}

function CheckRow({
  label,
  preview,
  ...props
}: { label: string; preview?: string } & React.ComponentProps<
  typeof Checkbox
>) {
  const id = React.useId();
  return (
    <div className="flex min-h-11 items-center gap-3">
      <Checkbox id={id} data-preview={preview} {...props} />
      <Label htmlFor={id} className="text-base font-normal">
        {label}
      </Label>
    </div>
  );
}

function RadioRow({
  value,
  label,
  preview,
  disabled,
}: {
  value: string;
  label: string;
  preview?: string;
  disabled?: boolean;
}) {
  const id = React.useId();
  return (
    <div className="flex min-h-11 items-center gap-3">
      <RadioGroupItem
        id={id}
        value={value}
        data-preview={preview}
        disabled={disabled}
      />
      <Label htmlFor={id} className="text-base font-normal">
        {label}
      </Label>
    </div>
  );
}

function SwitchRow({
  label,
  preview,
  ...props
}: { label: string; preview?: string } & React.ComponentProps<typeof Switch>) {
  const id = React.useId();
  return (
    <div className="flex min-h-11 items-center gap-3">
      <Switch id={id} data-preview={preview} {...props} />
      <Label htmlFor={id} className="text-base font-normal">
        {label}
      </Label>
    </div>
  );
}

function ChipsDemo() {
  const [seasons, setSeasons] = React.useState(["Summer"]);
  const [active, setActive] = React.useState(["Navy", "Cotton", "College"]);
  const toggle = (season: string) =>
    setSeasons((current) =>
      current.includes(season)
        ? current.filter((s) => s !== season)
        : [...current, season],
    );

  return (
    <div className="flex flex-col gap-6">
      <Row label="Filter chips">
        {["Summer", "Monsoon", "Winter"].map((season) => (
          <State
            key={season}
            label={seasons.includes(season) ? "Selected" : "Default"}
          >
            <FilterChip
              selected={seasons.includes(season)}
              onClick={() => toggle(season)}
            >
              {season}
            </FilterChip>
          </State>
        ))}
        <State label="Hover">
          <FilterChip data-preview="hover">Mild</FilterChip>
        </State>
        <State label="Focus">
          <FilterChip data-preview="focus">Linen</FilterChip>
        </State>
        <State label="Disabled">
          <FilterChip disabled>Wool</FilterChip>
        </State>
      </Row>
      <Row label="Active filters">
        {active.map((label) => (
          <RemovableChip
            key={label}
            label={label}
            onRemove={() =>
              setActive((current) => current.filter((item) => item !== label))
            }
          />
        ))}
        {active.length > 0 ? (
          <Button
            variant="quiet"
            className="min-h-9 px-3 text-sm"
            onClick={() => setActive([])}
          >
            Clear all
          </Button>
        ) : (
          <Button
            variant="quiet"
            className="min-h-9 px-3 text-sm"
            onClick={() => setActive(["Navy", "Cotton", "College"])}
          >
            Reset demo
          </Button>
        )}
      </Row>
    </div>
  );
}

function ToastDemo({ showOnLoad }: { showOnLoad: boolean }) {
  React.useEffect(() => {
    if (!showOnLoad) return;
    toast.success("Outfit saved", { duration: Infinity });
    toast.error("Couldn't save the outfit", {
      description: "Check your connection and try again.",
      duration: Infinity,
    });
  }, [showOnLoad]);

  return (
    <div className="flex flex-wrap gap-3">
      <Button variant="secondary" onClick={() => toast.success("Outfit saved")}>
        Show success
      </Button>
      <Button
        variant="secondary"
        onClick={() =>
          toast.error("Couldn't save the outfit", {
            description: "Check your connection and try again.",
          })
        }
      >
        Show error
      </Button>
    </div>
  );
}

function LoadMoreDemo() {
  const [shown, setShown] = React.useState(24);
  const [loading, setLoading] = React.useState(false);
  const loadMore = () => {
    setLoading(true);
    setTimeout(() => {
      setShown((count) => Math.min(count + 24, 60));
      setLoading(false);
    }, 600);
  };
  return (
    <LoadMore
      shown={shown}
      total={60}
      loading={loading}
      onLoadMore={loadMore}
    />
  );
}
