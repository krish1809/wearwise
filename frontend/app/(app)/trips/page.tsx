import type { Metadata } from "next";

import { TripsContent } from "./trips-content";

export const metadata: Metadata = { title: "Trips · WearWise" };

export default function Page() {
  return <TripsContent />;
}
