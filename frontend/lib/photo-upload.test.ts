import { expect, it } from "vitest";

import {
  NOT_A_PHOTO,
  PhotoProblem,
  preparePhoto,
  tooLarge,
} from "@/lib/photo-upload";

it("names the size of a file that's too big", () => {
  expect(tooLarge(30 * 1024 * 1024)).toBe(
    "That file is 30.0 MB. Photos can be up to 25 MB.",
  );
  expect(tooLarge(5 * 1024 * 1024)).toBeNull();
});

it("refuses a file that isn't an image before reading it", async () => {
  const pdf = new File(["%PDF"], "receipt.pdf", { type: "application/pdf" });

  await expect(preparePhoto(pdf)).rejects.toThrow(PhotoProblem);
  await expect(preparePhoto(pdf)).rejects.toThrow(NOT_A_PHOTO);
});

it("refuses an image the browser can't decode", async () => {
  // jsdom has no image decoder, like a browser given a format it doesn't know.
  const broken = new File(["not really"], "a.png", { type: "image/png" });

  await expect(preparePhoto(broken)).rejects.toThrow(NOT_A_PHOTO);
});
