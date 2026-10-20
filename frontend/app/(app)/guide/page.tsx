import type { Metadata } from "next";

import { GuideContent } from "./guide-content";

export const metadata: Metadata = { title: "Style Guide · WearWise" };

export default function GuidePage() {
  return <GuideContent />;
}
