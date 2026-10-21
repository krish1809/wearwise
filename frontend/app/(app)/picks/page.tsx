import type { Metadata } from "next";

import { PicksContent } from "./picks-content";

export const metadata: Metadata = { title: "Weekly picks · WearWise" };

export default function PicksPage() {
  return <PicksContent />;
}
