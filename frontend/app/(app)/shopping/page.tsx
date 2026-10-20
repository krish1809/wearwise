import type { Metadata } from "next";

import { ShoppingContent } from "./shopping-content";

export const metadata: Metadata = { title: "Shopping · WearWise" };

export default function ShoppingPage() {
  return <ShoppingContent />;
}
