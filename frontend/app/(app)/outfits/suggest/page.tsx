import type { Metadata } from "next";
import { Suspense } from "react";

import { PageLoading } from "@/components/app-shell";

import { SuggestContent } from "./suggest-content";

export const metadata: Metadata = { title: "Suggest outfits · WearWise" };

export default function SuggestPage() {
  return (
    // The piece to build around (?with=) is read from the address bar.
    <Suspense fallback={<PageLoading />}>
      <SuggestContent />
    </Suspense>
  );
}
