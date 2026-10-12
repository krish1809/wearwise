import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { Suspense } from "react";

import { Styleguide } from "./styleguide";

export const metadata: Metadata = {
  title: "Style guide · WearWise",
  robots: { index: false },
};

// A development tool for design review: every component in every state.
// Production builds answer 404 here.
export default function StyleguidePage() {
  if (process.env.NODE_ENV === "production") notFound();
  return (
    <Suspense>
      <Styleguide />
    </Suspense>
  );
}
