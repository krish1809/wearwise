import type { Metadata } from "next";
import { Suspense } from "react";

import { PageLoading } from "@/components/app-shell";

import { EditCandidateContent } from "./edit-candidate-content";

export const metadata: Metadata = { title: "Edit · Shopping · WearWise" };

export default function EditCandidatePage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <EditCandidateContent />
    </Suspense>
  );
}
