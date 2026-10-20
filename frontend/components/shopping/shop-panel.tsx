"use client";

import { ExternalLink } from "lucide-react";
import Link from "next/link";
import { useState } from "react";

import { PieceRow } from "@/components/shopping/piece-row";
import { Alert } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Skeleton } from "@/components/ui/skeleton";
import { toast } from "@/components/ui/toast";
import { problemFrom } from "@/lib/api/errors";
import { formatRupees } from "@/lib/money";
import {
  type CatalogProduct,
  useAddFromCatalog,
  useShop,
} from "@/lib/shopping";
import { cn, focusRing } from "@/lib/utils";

type Target = { archetypeId: string } | { candidateId: string };

/**
 * Where to find something: each shop's own search for it (the person browses there), their
 * usual spend as a guide, a way to bring back a product's link, and demo catalogue products
 * when a catalogue is loaded, clearly marked as not for sale.
 */
export function ShopPanel({
  target,
  name,
  trigger,
}: {
  target: Target;
  name: string;
  trigger: React.ReactNode;
}) {
  const [open, setOpen] = useState(false);
  const shop = useShop(target, open);

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>{trigger}</DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Find {name.toLowerCase()}</DialogTitle>
          <DialogDescription>
            WearWise doesn&apos;t sell anything. Search a shop, and paste the
            link of one you like to see what it would add.
          </DialogDescription>
        </DialogHeader>
        {shop.isError ? (
          <Alert tone="error">{problemFrom(shop.error).message}</Alert>
        ) : !shop.data ? (
          <div aria-busy="true" className="flex flex-col gap-2">
            <Skeleton className="h-11" />
            <Skeleton className="h-11" />
            <span role="status" className="sr-only">
              Loading
            </span>
          </div>
        ) : (
          <div className="flex flex-col gap-5">
            <section aria-labelledby="shops-heading">
              <h3 id="shops-heading" className="text-sm font-medium">
                Search the shops for &ldquo;{shop.data.query}&rdquo;
              </h3>
              {shop.data.price_cap !== null && (
                <p className="mt-1 text-sm text-ink-soft">
                  Look for under {formatRupees(shop.data.price_cap)}: your usual
                  spend on {shop.data.group_name.toLowerCase()}.
                </p>
              )}
              <ul className="mt-3 grid grid-cols-2 gap-2">
                {shop.data.links.map((link) => (
                  <li key={link.shop_id}>
                    <a
                      href={link.url}
                      target="_blank"
                      rel="noopener noreferrer nofollow"
                      className={cn(
                        "flex min-h-11 items-center justify-between gap-2 rounded-lg border border-line-strong/60 bg-surface px-4 font-medium hover:border-ink-soft",
                        focusRing,
                      )}
                    >
                      {link.shop}
                      <ExternalLink
                        aria-hidden
                        className="size-4 text-ink-soft"
                      />
                      <span className="sr-only">(opens in a new tab)</span>
                    </a>
                  </li>
                ))}
              </ul>
            </section>
            <p className="text-sm">
              Found one?{" "}
              <Link
                href="/shopping/new"
                className={cn(
                  "font-medium text-indigo underline underline-offset-4",
                  focusRing,
                )}
              >
                Paste its link
              </Link>{" "}
              to check it against your wardrobe.
            </p>
            {shop.data.products !== null && (
              <Demo products={shop.data.products} />
            )}
          </div>
        )}
      </DialogContent>
    </Dialog>
  );
}

function Demo({ products }: { products: CatalogProduct[] }) {
  const add = useAddFromCatalog();
  async function addProduct(product: CatalogProduct) {
    try {
      await add.mutateAsync(product.id);
      toast.success("Added to your list");
    } catch (error) {
      toast.error(problemFrom(error).message);
    }
  }
  return (
    <section aria-labelledby="demo-heading">
      <h3 id="demo-heading" className="text-sm font-medium">
        From the demo catalogue
      </h3>
      <p className="mt-1 text-sm text-ink-soft">
        Example products from an open dataset, not for sale and without prices,
        ranked by what each would add to your wardrobe.
      </p>
      {products.length === 0 ? (
        <p className="mt-3 text-sm text-ink-soft">
          Nothing of this kind in the catalogue that you don&apos;t already
          have.
        </p>
      ) : (
        <ul className="mt-3 flex flex-col gap-2">
          {products.map((product) => (
            <li key={product.id}>
              <PieceRow
                name={product.title}
                hex={product.hex}
                imageUrl={product.image_url}
              >
                <span className="flex shrink-0 items-center gap-2">
                  <span className="rounded-full bg-tile px-2 py-0.5 text-xs font-medium">
                    Demo
                  </span>
                  <Button
                    variant="quiet"
                    disabled={add.isPending}
                    onClick={() => void addProduct(product)}
                  >
                    Add
                    <span className="sr-only">
                      {" "}
                      {product.title} to your list
                    </span>
                  </Button>
                </span>
              </PieceRow>
              <p className="mt-0.5 pl-15 text-xs text-ink-soft">
                {product.coverage_gain > 0
                  ? `${product.new_outfits} new good ${product.new_outfits === 1 ? "outfit" : "outfits"} where you're short`
                  : "Adds nothing where you're short"}
                {product.closest && product.redundancy >= 0.6
                  ? `; close to your ${product.closest.toLowerCase()}`
                  : ""}
              </p>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
