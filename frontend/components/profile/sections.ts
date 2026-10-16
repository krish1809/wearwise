import { ABOUT_FIELDS, AboutForm } from "@/components/profile/about-form";
import { BUDGET_FIELDS, BudgetForm } from "@/components/profile/budget-form";
import {
  MEASUREMENTS_FIELDS,
  MeasurementsForm,
} from "@/components/profile/measurements-form";
import {
  OCCASIONS_FIELDS,
  OccasionsForm,
} from "@/components/profile/occasions-form";
import type { SectionFormProps } from "@/components/profile/section-form";
import { SIZES_FIELDS, SizesForm } from "@/components/profile/sizes-form";
import { STYLE_FIELDS, StyleForm } from "@/components/profile/style-form";
import type { ProfileChanges } from "@/lib/profile";

export type ProfileSection = {
  id: string;
  title: string;
  /** One line under the title, saying why WearWise asks. */
  intro: string;
  Form: (props: SectionFormProps) => React.ReactNode;
  /** The fields this section saves, so Settings can clear exactly these. */
  fields: readonly (keyof ProfileChanges)[];
};

/** The six onboarding steps, in order. Settings shows the same forms. */
export const PROFILE_SECTIONS: readonly ProfileSection[] = [
  {
    id: "about",
    title: "What you shop",
    intro: "So WearWise shows the right categories first.",
    Form: AboutForm,
    fields: ABOUT_FIELDS,
  },
  {
    id: "sizes",
    title: "Sizes and fit",
    intro: "Your usual sizes, so you don't have to remember them.",
    Form: SizesForm,
    fields: SIZES_FIELDS,
  },
  {
    id: "measurements",
    title: "Measurements",
    intro: "Handy to have when a brand's sizes don't match your usual ones.",
    Form: MeasurementsForm,
    fields: MEASUREMENTS_FIELDS,
  },
  {
    id: "occasions",
    title: "Occasions",
    intro: "WearWise will plan outfits around these.",
    Form: OccasionsForm,
    fields: OCCASIONS_FIELDS,
  },
  {
    id: "style",
    title: "Style and colours",
    intro: "What you like wearing, and what you'd rather not.",
    Form: StyleForm,
    fields: STYLE_FIELDS,
  },
  {
    id: "budget",
    title: "Budget",
    intro: "So suggestions to buy something stay within what you spend.",
    Form: BudgetForm,
    fields: BUDGET_FIELDS,
  },
];
