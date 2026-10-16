import type { Metadata } from "next";

import { WearLogContent } from "./wear-log-content";

export const metadata: Metadata = { title: "Wear log · WearWise" };

export default function WearLogPage() {
  return <WearLogContent />;
}
