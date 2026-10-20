import type { Metadata } from "next";

import { WeekContent } from "./week-content";

export const metadata: Metadata = { title: "My Week · WearWise" };

export default function WeekPage() {
  return <WeekContent />;
}
