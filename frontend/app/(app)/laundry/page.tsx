import type { Metadata } from "next";

import { LaundryContent } from "./laundry-content";

export const metadata: Metadata = { title: "Laundry · WearWise" };

export default function LaundryPage() {
  return <LaundryContent />;
}
