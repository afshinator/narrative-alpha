import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Pill } from "./Pill";

describe("Pill", () => {
  it("renders children text", () => {
    render(<Pill>Fab 7</Pill>);
    expect(screen.getByText("Fab 7")).toBeInTheDocument();
  });

  it("applies node-pill class", () => {
    render(<Pill>Fab 7</Pill>);
    expect(screen.getByText("Fab 7").className).toContain("node-pill");
  });
});
