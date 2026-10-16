import type { Metadata } from "next";

import { SettingsContent } from "./settings-content";

export const metadata: Metadata = { title: "Settings · WearWise" };

export default function SettingsPage() {
  return <SettingsContent />;
}
