import type { Metadata } from "next";
import { Suspense } from "react";

import { PageLoading } from "@/components/app-shell";

import { EditItemContent } from "./edit-item-content";

export const metadata: Metadata = { title: "Edit item · WearWise" };

export default function EditItemPage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <EditItemContent />
    </Suspense>
  );
}
