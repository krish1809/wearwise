import type { Metadata } from "next";

import { NewTripContent } from "./new-trip-content";

export const metadata: Metadata = { title: "Plan a trip · WearWise" };

export default function Page() {
  return <NewTripContent />;
}
