import type { Metadata } from "next";
import { Suspense } from "react";

import { PageLoading } from "@/components/app-shell";

import { CandidateView } from "./candidate-view";

export const metadata: Metadata = { title: "Shopping · WearWise" };

export default function CandidatePage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <CandidateView />
    </Suspense>
  );
}
