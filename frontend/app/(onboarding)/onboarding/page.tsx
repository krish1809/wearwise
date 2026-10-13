import type { Metadata } from "next";

import { OnboardingFlow } from "./onboarding-flow";

export const metadata: Metadata = { title: "Set up · WearWise" };

export default function OnboardingPage() {
  return <OnboardingFlow />;
}
