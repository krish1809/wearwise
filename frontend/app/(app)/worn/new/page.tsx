import type { Metadata } from "next";

import { LogItemsContent } from "./log-items-content";

export const metadata: Metadata = { title: "Log what you wore · WearWise" };

export default function LogItemsPage() {
  return <LogItemsContent />;
}
