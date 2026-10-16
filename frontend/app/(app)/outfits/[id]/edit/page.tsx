import type { Metadata } from "next";
import { Suspense } from "react";

import { PageLoading } from "@/components/app-shell";

import { EditOutfitContent } from "./edit-outfit-content";

export const metadata: Metadata = { title: "Edit outfit · WearWise" };

export default function EditOutfitPage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <EditOutfitContent />
    </Suspense>
  );
}
