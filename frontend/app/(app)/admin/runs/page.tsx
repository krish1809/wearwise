import type { Metadata } from "next";

import { RunsContent } from "./runs-content";

export const metadata: Metadata = { title: "Agent runs · WearWise" };

export default function AdminRunsPage() {
  return <RunsContent />;
}
