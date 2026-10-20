import type { Metadata } from "next";
import { Suspense } from "react";

import { PageLoading } from "@/components/app-shell";

import { TripContent } from "./trip-content";

export const metadata: Metadata = { title: "Trip · WearWise" };

export default function TripPage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <TripContent />
    </Suspense>
  );
}
