import type { Metadata } from "next";

import { NewCandidateContent } from "./new-candidate-content";

export const metadata: Metadata = { title: "Add to shopping list · WearWise" };

export default function NewCandidatePage() {
  return <NewCandidateContent />;
}
