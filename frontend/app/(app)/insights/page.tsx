import type { Metadata } from "next";

import { InsightsContent } from "./insights-content";

export const metadata: Metadata = { title: "Insights · WearWise" };

export default function InsightsPage() {
  return <InsightsContent />;
}
