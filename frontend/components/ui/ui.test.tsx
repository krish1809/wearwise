import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { initials } from "@/components/ui/avatar-menu";
import { Button } from "@/components/ui/button";
import { FilterChip, RemovableChip } from "@/components/ui/chip";
import { Field } from "@/components/ui/field";
import { Input } from "@/components/ui/input";

afterEach(() => {
  cleanup();
});

describe("Button", () => {
  it("ignores clicks and says it is busy while loading", () => {
    const onClick = vi.fn();
    render(
      <Button loading onClick={onClick}>
        Saving
      </Button>,
    );

    const button = screen.getByRole("button", { name: "Saving" });
    fireEvent.click(button);

    expect(onClick).not.toHaveBeenCalled();
    expect(button.getAttribute("aria-busy")).toBe("true");
  });
});

describe("chips", () => {
  it("a filter chip reports whether it is selected", () => {
    render(
      <>
        <FilterChip selected>Summer</FilterChip>
        <FilterChip>Winter</FilterChip>
      </>,
    );

    expect(
      screen
        .getByRole("button", { name: "Summer" })
        .getAttribute("aria-pressed"),
    ).toBe("true");
    expect(
      screen
        .getByRole("button", { name: "Winter" })
        .getAttribute("aria-pressed"),
    ).toBe("false");
  });

  it("a removable chip's button names what it removes", () => {
    const onRemove = vi.fn();
    render(<RemovableChip label="Navy" onRemove={onRemove} />);

    fireEvent.click(screen.getByRole("button", { name: "Remove Navy" }));

    expect(onRemove).toHaveBeenCalledOnce();
  });
});

describe("Field", () => {
  it("ties the label, hint, and error to the control", () => {
    render(
      <Field label="Password" hint="At least 12 characters." error="Too short.">
        {(control) => <Input type="password" {...control} />}
      </Field>,
    );

    const input = screen.getByLabelText("Password");
    const describedBy = input.getAttribute("aria-describedby") ?? "";

    expect(input.getAttribute("aria-invalid")).toBe("true");
    expect(
      describedBy
        .split(" ")
        .map((id) => document.getElementById(id)?.textContent),
    ).toEqual(["At least 12 characters.", "Too short."]);
  });
});

describe("initials", () => {
  it.each([
    ["Sam Lee", "sam@example.com", "SL"],
    ["Priya", "priya@example.com", "PR"],
    [null, "zoe@example.com", "Z"],
    ["  ", "kai@example.com", "K"],
  ])("%s / %s gives %s", (name, email, expected) => {
    expect(initials(name, email)).toBe(expected);
  });
});
