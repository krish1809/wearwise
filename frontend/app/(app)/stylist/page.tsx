import type { Metadata } from "next";
import { Suspense } from "react";

import { PageLoading } from "@/components/app-shell";

import { StylistContent } from "./stylist-content";

export const metadata: Metadata = { title: "Stylist · WearWise" };

export default function StylistPage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <StylistContent />
    </Suspense>
  );
}
