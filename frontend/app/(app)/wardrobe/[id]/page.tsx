import type { Metadata } from "next";
import { Suspense } from "react";

import { PageLoading } from "@/components/app-shell";

import { ItemView } from "./item-view";

export const metadata: Metadata = { title: "Item · WearWise" };

export default function ItemPage() {
  return (
    <Suspense fallback={<PageLoading />}>
      <ItemView />
    </Suspense>
  );
}
