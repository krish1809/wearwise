import type { Metadata } from "next";

import { ColourMap } from "./colour-map";

export const metadata: Metadata = { title: "Colour map · WearWise" };

export default function ColourMapPage() {
  return <ColourMap />;
}
