import { describe, it, expect, beforeEach } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { FontSizeControl } from "./FontSizeControl";

describe("FontSizeControl", () => {
  beforeEach(() => {
    document.documentElement.removeAttribute("data-font-size");
  });

  it("renders 3 size buttons", () => {
    render(<FontSizeControl />);
    expect(screen.getByTitle("Small")).toBeInTheDocument();
    expect(screen.getByTitle("Medium")).toBeInTheDocument();
    expect(screen.getByTitle("Large")).toBeInTheDocument();
  });

  it("sets Medium active by default", () => {
    render(<FontSizeControl />);
    const btn = screen.getByTitle("Medium");
    expect(btn.className).toContain("active");
  });

  it("clicking Large sets data-font-size=lg on html", () => {
    render(<FontSizeControl />);
    fireEvent.click(screen.getByTitle("Large"));
    expect(document.documentElement.getAttribute("data-font-size")).toBe("lg");
  });

  it("clicking Small sets data-font-size=sm on html", () => {
    render(<FontSizeControl />);
    fireEvent.click(screen.getByTitle("Small"));
    expect(document.documentElement.getAttribute("data-font-size")).toBe("sm");
  });

  it("clicking Small then Medium resets to md", () => {
    render(<FontSizeControl />);
    fireEvent.click(screen.getByTitle("Small"));
    fireEvent.click(screen.getByTitle("Medium"));
    expect(document.documentElement.getAttribute("data-font-size")).toBe("md");
  });
});
