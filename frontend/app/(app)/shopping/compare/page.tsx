import type { Metadata } from "next";
import { Suspense } from "react";

import { PageLoading } from "@/components/app-shell";

import { CompareContent } from "./compare-content";

export const metadata: Metadata = { title: "Compare · Shopping · WearWise" };

export default function ComparePage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <CompareContent />
    </Suspense>
  );
}
