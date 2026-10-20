import type { Metadata } from "next";

import { BudgetContent } from "./budget-content";

export const metadata: Metadata = { title: "Split a budget · WearWise" };

export default function BudgetPage() {
  return <BudgetContent />;
}
