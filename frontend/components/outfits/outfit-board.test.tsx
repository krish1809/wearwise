import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, it } from "vitest";

import { REFERENCE } from "@/components/profile/test-data";

import { type BoardPiece, OutfitBoard, SwatchStrip } from "./outfit-board";

afterEach(cleanup);

const slots = REFERENCE.slots.map((slot, position) => ({ ...slot, position }));
const familyHex = new Map(REFERENCE.color_families.map((c) => [c.id, c.hex]));

const piece = (
  slot: string,
  name: string,
  hex: string | null = null,
): BoardPiece => ({
  slot,
  name,
  removed: false,
  item: { color_primary: "navy", color_hex: hex, photo: null },
});

it("lays core pieces down the left and the layer and accessories down the right", () => {
  render(
    <OutfitBoard
      pieces={[
        piece("watch", "Steel watch"),
        piece("footwear", "Brown loafers"),
        piece("layer", "Denim jacket"),
        piece("top", "Navy shirt"),
        piece("bottom", "Olive chinos"),
      ]}
      slots={slots}
      familyHex={familyHex}
    />,
  );

  const main = within(screen.getByRole("list", { name: "Main pieces" }));
  const side = within(
    screen.getByRole("list", { name: "Layer and accessories" }),
  );
  expect(main.getAllByRole("listitem").map((li) => li.textContent)).toEqual([
    "Navy shirt",
    "Olive chinos",
    "Brown loafers",
  ]);
  expect(side.getAllByRole("listitem").map((li) => li.textContent)).toEqual([
    "Denim jacket",
    "Steel watch",
  ]);
});

it("shows a deleted piece as removed", () => {
  render(
    <OutfitBoard
      pieces={[
        { slot: "footwear", name: "Brown loafers", removed: true, item: null },
      ]}
      slots={slots}
      familyHex={familyHex}
    />,
  );

  expect(screen.getByText("Removed")).toBeDefined();
  expect(screen.getByText("Brown loafers").className).toContain("line-through");
});

it("strips the outfit's colours, measured first, then the family's", () => {
  const { container } = render(
    <SwatchStrip
      pieces={[piece("top", "Shirt", "#123456"), piece("bottom", "Chinos")]}
      familyHex={familyHex}
    />,
  );

  const swatches = container.querySelectorAll("span");
  expect([...swatches].map((s) => s.style.background)).toEqual([
    "rgb(18, 52, 86)",
    "rgb(31, 42, 68)",
  ]);
});
