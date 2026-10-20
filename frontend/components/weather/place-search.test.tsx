import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { api } from "@/lib/api/client";
import { apiAnswer, renderWithQueries } from "@/lib/test-utils";

import { PlaceSearch } from "./place-search";

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

const PUNE = {
  label: "Pune, Maharashtra, India",
  name: "Pune",
  region: "Maharashtra",
  country: "India",
  latitude: 18.52,
  longitude: 73.86,
};

it("finds places by name and picks the right one", async () => {
  vi.spyOn(api, "GET").mockResolvedValue(
    apiAnswer(200, [
      PUNE,
      { ...PUNE, label: "Pune, Oecusse, Timor-Leste", country: "Timor-Leste" },
    ]) as never,
  );
  const onChange = vi.fn();
  renderWithQueries(
    <PlaceSearch
      label="City"
      hint="For the forecast."
      value={null}
      onChange={onChange}
    />,
  );

  fireEvent.change(screen.getByLabelText("City"), {
    target: { value: "Pune" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Find" }));
  fireEvent.click(
    await screen.findByRole("radio", { name: "Pune, Maharashtra, India" }),
  );

  await waitFor(() =>
    expect(onChange).toHaveBeenCalledWith({
      label: "Pune, Maharashtra, India",
      latitude: 18.52,
      longitude: 73.86,
    }),
  );
});

it("says when nothing matches", async () => {
  vi.spyOn(api, "GET").mockResolvedValue(apiAnswer(200, []) as never);
  renderWithQueries(
    <PlaceSearch
      label="City"
      hint="For the forecast."
      value={null}
      onChange={vi.fn()}
    />,
  );

  fireEvent.change(screen.getByLabelText("City"), {
    target: { value: "Xyzzy" },
  });
  fireEvent.click(screen.getByRole("button", { name: "Find" }));

  expect(
    await screen.findByText("No places match that name. Check the spelling."),
  ).toBeDefined();
});

it("shows a chosen place with a way to change or remove it", () => {
  const onChange = vi.fn();
  renderWithQueries(
    <PlaceSearch
      label="City"
      hint="For the forecast."
      value={{ label: PUNE.label, latitude: 18.52, longitude: 73.86 }}
      onChange={onChange}
    />,
  );

  expect(screen.getByText("Pune, Maharashtra, India")).toBeDefined();
  fireEvent.click(screen.getByRole("button", { name: "Remove" }));
  expect(onChange).toHaveBeenCalledWith(null);
});
