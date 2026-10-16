import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { Button } from "@/components/ui/button";
import { api } from "@/lib/api/client";
import type { Profile } from "@/lib/profile";
import { renderWithQueries, sentBody, typeInto } from "@/lib/test-utils";

import { BudgetForm } from "./budget-form";
import { MeasurementsForm } from "./measurements-form";
import type { SectionFormProps } from "./section-form";
import { SizesForm } from "./sizes-form";
import { StyleForm } from "./style-form";
import { echoProfilePatch, makeProfile, REFERENCE } from "./test-data";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderForm(
  Form: (props: SectionFormProps) => React.ReactNode,
  profile: Profile,
) {
  const patch = vi
    .spyOn(api, "PATCH")
    .mockImplementation(echoProfilePatch(profile));
  renderWithQueries(
    <Form
      profile={profile}
      reference={REFERENCE}
      actions={() => <Button type="submit">Save</Button>}
    />,
  );
  return {
    patch,
    save: () => fireEvent.click(screen.getByRole("button", { name: "Save" })),
    sent: () => sentBody(patch),
  };
}

it("switches units for display and saves untouched values exactly", async () => {
  const { save, sent } = renderForm(
    MeasurementsForm,
    makeProfile({ height_cm: 175.3, measurements: { waist: 81.4 } }),
  );

  fireEvent.click(screen.getByRole("radio", { name: "Inches" }));

  expect(screen.getByLabelText("Waist (inches)")).toHaveProperty("value", "32");
  expect(screen.getByLabelText("Height (inches)")).toHaveProperty(
    "value",
    "69",
  );
  save();
  await waitFor(() =>
    expect(sent()).toEqual({
      units: "in",
      height_cm: 175.3,
      measurements: {
        chest: null,
        waist: 81.4,
        hips: null,
        shoulder: null,
        inseam: null,
      },
    }),
  );
});

it("saves a value typed in inches in cm", async () => {
  const { save, sent } = renderForm(
    MeasurementsForm,
    makeProfile({ units: "in" }),
  );

  typeInto("Waist (inches)", "32");
  save();

  await waitFor(() =>
    expect(sent()).toMatchObject({ measurements: { waist: 81.3 } }),
  );
});

it("explains a measurement out of range in the chosen units", async () => {
  const { save, patch } = renderForm(
    MeasurementsForm,
    makeProfile({ units: "in" }),
  );

  typeInto("Chest or bust (inches)", "5");
  save();

  expect(
    await screen.findByText("Enter a number between 19.7 and 78.7 in."),
  ).toBeDefined();
  expect(patch).not.toHaveBeenCalled();
});

it("keeps the extra measurements behind More until needed", () => {
  renderForm(MeasurementsForm, makeProfile());
  expect(screen.queryByLabelText("Hips (cm)")).toBeNull();

  fireEvent.click(screen.getByRole("button", { name: "More measurements" }));

  expect(screen.getByLabelText("Hips (cm)")).toBeDefined();
});

it("moves a colour out of avoided when it is loved", async () => {
  const { save, sent } = renderForm(
    StyleForm,
    makeProfile({ avoided_colors: ["navy", "orange"] }),
  );

  const navyButtons = screen.getAllByRole("button", { name: "Navy" });
  fireEvent.click(navyButtons[0]);
  save();

  await waitFor(() =>
    expect(sent()).toEqual({
      style_profile_ids: [],
      preferred_colors: ["navy"],
      avoided_colors: ["orange"],
    }),
  );
});

it("asks for a size when only a sizing system was chosen", async () => {
  const { save, patch } = renderForm(SizesForm, makeProfile());

  fireEvent.change(screen.getAllByLabelText("Sizing system")[0], {
    target: { value: "eu" },
  });
  save();

  expect(
    await screen.findByText(
      "Enter a size, or set the sizing system back to Any.",
    ),
  ).toBeDefined();
  expect(patch).not.toHaveBeenCalled();
});

it("saves sizes as written, with their system", async () => {
  const { save, sent } = renderForm(SizesForm, makeProfile());

  fireEvent.change(screen.getAllByLabelText("Size")[2], {
    target: { value: " 9 " },
  });
  fireEvent.change(screen.getAllByLabelText("Sizing system")[2], {
    target: { value: "in_uk" },
  });
  fireEvent.click(screen.getByRole("radio", { name: "Slim" }));
  save();

  await waitFor(() =>
    expect(sent()).toEqual({
      sizes: { shoe: { label: "9", system: "in_uk" } },
      fit_preference: "slim",
    }),
  );
});

it("saves budgets in paise", async () => {
  const { save, sent } = renderForm(BudgetForm, makeProfile());

  typeInto("Monthly clothing budget, in rupees", "5,000");
  typeInto("Tops", "1499.50");
  save();

  await waitFor(() =>
    expect(sent()).toEqual({
      budget_monthly: 500000,
      category_budgets: { tops: 149950 },
    }),
  );
});
