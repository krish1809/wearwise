import type { Metadata } from "next";
import { Suspense } from "react";

import { PageLoading } from "@/components/app-shell";

import { OutfitView } from "./outfit-view";

export const metadata: Metadata = { title: "Outfit · WearWise" };

export default function OutfitPage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <OutfitView />
    </Suspense>
  );
}
