import type { Metadata } from "next";

import { NewItemContent } from "./new-item-content";

export const metadata: Metadata = { title: "Add item · WearWise" };

export default function NewItemPage() {
  return <NewItemContent />;
}
