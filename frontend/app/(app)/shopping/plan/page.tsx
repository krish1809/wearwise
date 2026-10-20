import type { Metadata } from "next";

import { PlanContent } from "./plan-content";

export const metadata: Metadata = { title: "Starter wardrobe · WearWise" };

export default function PlanPage() {
  return <PlanContent />;
}
