import { cleanup, fireEvent, screen, waitFor } from "@testing-library/react";
import { afterEach, expect, it, vi } from "vitest";

import { makeProfile, REFERENCE } from "@/components/profile/test-data";
import { api } from "@/lib/api/client";
import { apiAnswer, renderWithQueries } from "@/lib/test-utils";
import type { NewItem } from "@/lib/wardrobe";

import { ItemForm } from "./item-form";
import { CATEGORIES } from "./test-data";

// jsdom can't decode images; the real resizing is checked in the browser walkthrough.
vi.mock("@/lib/photo-upload", async (original) => ({
  ...(await original<typeof import("@/lib/photo-upload")>()),
  preparePhoto: async () => new Blob(["jpeg"], { type: "image/jpeg" }),
}));

afterEach(() => {
  cleanup();
  vi.restoreAllMocks();
});

function renderForm(sections: string[] = ["menswear"]) {
  const onSubmit = vi.fn<(body: NewItem, again: boolean) => Promise<null>>(
    async () => null,
  );
  renderWithQueries(
    <ItemForm
      reference={REFERENCE}
      categories={CATEGORIES}
      profile={makeProfile({ sections })}
      saving={false}
      onSubmit={onSubmit as never}
    />,
  );
  return onSubmit;
}

const chooseCategory = (id: string) =>
  fireEvent.change(screen.getByLabelText("Category"), {
    target: { value: id },
  });

it("asks for a category and a colour before saving", async () => {
  const onSubmit = renderForm();

  fireEvent.click(screen.getByRole("button", { name: "Add item" }));

  expect(
    await screen.findByText("Choose what kind of item it is."),
  ).toBeDefined();
  expect(screen.getByText("Choose its main colour.")).toBeDefined();
  expect(onSubmit).not.toHaveBeenCalled();
});

it("sends a category and a colour, leaving the defaults to the category", async () => {
  const onSubmit = renderForm();

  chooseCategory("tshirt");
  fireEvent.click(screen.getByRole("button", { name: "Navy" }));
  fireEvent.click(screen.getByRole("button", { name: "Add item" }));

  await waitFor(() => expect(onSubmit).toHaveBeenCalled());
  const body = onSubmit.mock.calls[0][0];
  expect(body).toMatchObject({
    category_id: "tshirt",
    color_primary: "navy",
    pattern: "solid",
    status: "available",
  });
  expect(body).not.toHaveProperty("formality");
  expect(body).not.toHaveProperty("wears_before_wash");
  expect(body).not.toHaveProperty("photo_id");
});

it("offers only the sections shopped until show all is on", () => {
  renderForm(["menswear"]);
  const options = () =>
    Array.from(
      screen.getByLabelText("Category").querySelectorAll("option"),
    ).map((option) => option.textContent);

  expect(options()).not.toContain("Blouse");
  fireEvent.click(screen.getByRole("switch", { name: "Show all categories" }));
  expect(options()).toContain("Blouse");
});

it("takes the colour suggested by the photo, and sends the photo", async () => {
  vi.spyOn(api, "POST").mockResolvedValue(
    apiAnswer(201, {
      id: "photo-1",
      url: "/api/v1/photos/photo-1/full",
      thumb_url: "/api/v1/photos/photo-1/thumb",
      width: 1200,
      height: 1600,
      dominant_hex: "#1F2A44",
      suggested_color: "navy",
    }) as never,
  );
  const onSubmit = renderForm();
  const input = document.querySelector(
    'input[type="file"]',
  ) as HTMLInputElement;

  fireEvent.change(input, {
    target: { files: [new File(["x"], "shirt.jpg", { type: "image/jpeg" })] },
  });

  expect(
    await screen.findByText(
      "Suggested from the photo. Change it if it's wrong.",
    ),
  ).toBeDefined();
  expect(
    screen.getByRole("button", { name: "Navy" }).getAttribute("aria-pressed"),
  ).toBe("true");
  chooseCategory("tshirt");
  fireEvent.click(screen.getByRole("button", { name: "Add item" }));
  await waitFor(() =>
    expect(onSubmit.mock.calls[0][0]).toMatchObject({
      photo_id: "photo-1",
      color_hex: "#1F2A44",
    }),
  );
});

it("shows why a photo was refused", async () => {
  vi.spyOn(api, "POST").mockResolvedValue(
    apiAnswer(422, {
      error: {
        code: "photo_rejected",
        message: "That file isn't a photo WearWise can read.",
        fields: { file: "That file isn't a photo WearWise can read." },
      },
    }) as never,
  );
  renderForm();
  const input = document.querySelector(
    'input[type="file"]',
  ) as HTMLInputElement;

  fireEvent.change(input, {
    target: { files: [new File(["x"], "a.jpg", { type: "image/jpeg" })] },
  });

  expect((await screen.findByRole("alert")).textContent).toBe(
    "That file isn't a photo WearWise can read.",
  );
});
