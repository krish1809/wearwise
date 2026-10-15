import type { Metadata } from "next";

import { OutfitsContent } from "./outfits-content";

export const metadata: Metadata = { title: "Outfits · WearWise" };

export default function OutfitsPage() {
  return <OutfitsContent />;
}
