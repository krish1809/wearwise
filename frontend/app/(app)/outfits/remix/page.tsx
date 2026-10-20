import type { Metadata } from "next";

import { RemixContent } from "./remix-content";

export const metadata: Metadata = { title: "Remix · WearWise" };

export default function RemixPage() {
  return <RemixContent />;
}
