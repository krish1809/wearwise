import type { Metadata } from "next";

import { AdminContent } from "./admin-content";

export const metadata: Metadata = { title: "Counts · WearWise" };

export default function AdminPage() {
  return <AdminContent />;
}
