import type { Metadata } from "next";

import { NewOutfitContent } from "./new-outfit-content";

export const metadata: Metadata = { title: "New outfit · WearWise" };

export default function NewOutfitPage() {
  return <NewOutfitContent />;
}
