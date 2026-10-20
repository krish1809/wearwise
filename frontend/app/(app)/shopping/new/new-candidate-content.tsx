"use client";

import { Link2 } from "lucide-react";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  CandidateForm,
  type Prefill,
} from "@/components/shopping/candidate-form";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Card, CardDescription, CardTitle } from "@/components/ui/card";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";
import { toast } from "@/components/ui/toast";
import { BackLink, WardrobeData } from "@/components/wardrobe/wardrobe-data";
import { problemFrom } from "@/lib/api/errors";
import { formatRupees } from "@/lib/money";
import {
  type LinkPreview,
  siteOf,
  useCreateCandidate,
  usePreviewLink,
} from "@/lib/shopping";

export function NewCandidateContent() {
  const router = useRouter();
  const create = useCreateCandidate();
  // Each read gives the form a fresh start with what the page said.
  const [read, setRead] = useState<{
    preview: LinkPreview;
    key: number;
  } | null>(null);

  return (
    <div className="flex flex-col gap-6">
      <BackLink href="/shopping">Shopping</BackLink>
      <div>
        <h1 className="font-display text-2xl font-semibold tracking-tight">
          Something you&apos;re thinking of buying
        </h1>
        <p className="mt-1 max-w-prose text-ink-soft">
          Paste its link, or describe it like an item in your wardrobe. A colour
          and a category are enough to see what it would add.
        </p>
      </div>
      <LinkReader onRead={(preview) => setRead({ preview, key: Date.now() })} />
      <WardrobeData>
        {({ reference, categories, profile }) => (
          <CandidateForm
            key={read?.key ?? 0}
            reference={reference}
            categories={categories}
            profile={profile}
            prefill={read ? prefillFrom(read.preview) : undefined}
            // "From a link" only when the page's details were actually read.
            source={read?.preview.outcome === "ok" ? "link" : "manual"}
            saving={create.isPending}
            onSubmit={async (body) => {
              try {
                const made = await create.mutateAsync(body);
                toast.success(`${made.display_name} added to your list`);
                router.push(`/shopping/${made.id}`);
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

function prefillFrom(preview: LinkPreview): Prefill {
  if (preview.outcome !== "ok") return { url: preview.url };
  return {
    name: preview.title,
    brand: preview.brand,
    url: preview.url,
    price: preview.price,
    category_id: preview.category_id,
    color_primary: preview.color_primary,
    fabric: preview.fabric,
    image_url: preview.image_url,
  };
}

/** Paste a product link; the page's own preview data fills the form, to be checked. */
function LinkReader({ onRead }: { onRead: (preview: LinkPreview) => void }) {
  const previewLink = usePreviewLink();
  const [url, setUrl] = useState("");
  const [error, setError] = useState<string | undefined>();
  const [result, setResult] = useState<LinkPreview | null>(null);

  async function readIt() {
    if (!/^https?:\/\//i.test(url.trim())) {
      setError("Paste a link that starts with https://.");
      return;
    }
    setError(undefined);
    try {
      const preview = await previewLink.mutateAsync(url.trim());
      if (preview.outcome === "not_a_web_link") {
        setError("Paste a link that starts with https://.");
        return;
      }
      setResult(preview);
      onRead(preview);
    } catch (failure) {
      setError(problemFrom(failure).message);
    }
  }

  const site = result ? (result.site ?? siteOf(result.url) ?? "The shop") : "";
  return (
    <Card className="max-w-2xl">
      <CardTitle className="flex items-center gap-2">
        <Link2 aria-hidden className="size-5" />
        From a link
      </CardTitle>
      <CardDescription className="mt-1">
        WearWise reads what the page tells link previews (name, picture, price)
        once, if the shop allows it. You check every detail before saving.
      </CardDescription>
      <form
        noValidate
        className="mt-4 flex flex-wrap items-start gap-3"
        onSubmit={(event) => {
          event.preventDefault();
          void readIt();
        }}
      >
        <Field
          label="Product link"
          error={error}
          className="min-w-0 flex-1 basis-64"
        >
          {(control) => (
            <Input
              type="url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://"
              autoComplete="off"
              maxLength={2000}
              {...control}
            />
          )}
        </Field>
        <Button
          type="submit"
          variant="secondary"
          loading={previewLink.isPending}
          className="sm:mt-7"
        >
          Read the page
        </Button>
      </form>
      {result && (
        <div aria-live="polite" className="mt-4">
          {result.outcome === "ok" ? (
            <Alert>
              Read from {site}. Check each detail below: shops describe things
              their own way.
              {result.other_currency &&
                ` The price on the page is ${result.other_currency}, so it's left out.`}
              {result.price !== null &&
                ` Price on the page: ${formatRupees(result.price)}.`}
            </Alert>
          ) : result.outcome === "blocked" ? (
            <Alert>
              {site} doesn&apos;t allow apps like WearWise to read its pages, so
              nothing was read. The link is kept: fill in the rest yourself.
            </Alert>
          ) : result.outcome === "not_product" ? (
            <Alert>
              That page doesn&apos;t describe a product (it may ask you to sign
              in first). The link is kept: fill in the rest yourself.
            </Alert>
          ) : (
            <Alert>
              Couldn&apos;t read that page: the shop didn&apos;t answer, or
              turned WearWise away. The link is kept: fill in the rest yourself.
            </Alert>
          )}
        </div>
      )}
    </Card>
  );
}
