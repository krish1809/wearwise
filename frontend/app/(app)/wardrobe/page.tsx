import type { Metadata } from "next";
import { Suspense } from "react";

import { PageLoading } from "@/components/app-shell";

import { WardrobeContent } from "./wardrobe-content";

export const metadata: Metadata = { title: "Wardrobe · WearWise" };

export default function WardrobePage() {
  return (
    // The filters are read from the address bar, which is only known in the browser.
    <Suspense fallback={<PageLoading />}>
      <WardrobeContent />
    </Suspense>
  );
}
