import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Badge } from "./Badge";

describe("Badge", () => {
  it("renders the label text", () => {
    render(<Badge level="HIGH" label="0.65 HIGH" />);
    expect(screen.getByText("0.65 HIGH")).toBeInTheDocument();
  });

  it("applies badge-high class for HIGH level", () => {
    render(<Badge level="HIGH" label="0.65 HIGH" />);
    const el = screen.getByText("0.65 HIGH");
    expect(el.className).toContain("badge-high");
  });

  it("applies badge-med class for MED level", () => {
    render(<Badge level="MED" label="0.30 MED" />);
    const el = screen.getByText("0.30 MED");
    expect(el.className).toContain("badge-med");
  });

  it("applies badge-low class for LOW level", () => {
    render(<Badge level="LOW" label="0.10 LOW" />);
    const el = screen.getByText("0.10 LOW");
    expect(el.className).toContain("badge-low");
  });
});
