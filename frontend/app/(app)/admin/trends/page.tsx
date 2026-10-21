import type { Metadata } from "next";

import { TrendsContent } from "./trends-content";

export const metadata: Metadata = { title: "Trends · WearWise" };

export default function AdminTrendsPage() {
  return <TrendsContent />;
}
