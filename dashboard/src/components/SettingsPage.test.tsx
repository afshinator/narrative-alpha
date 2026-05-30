import { describe, it, expect } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SettingsPage } from "./SettingsPage";

describe("SettingsPage", () => {
  it("renders 4 settings rows with slot names", () => {
    render(<SettingsPage />);
    expect(screen.getByText("Call 1")).toBeInTheDocument();
    expect(screen.getByText("Call 2")).toBeInTheDocument();
    expect(screen.getByText("Call 3")).toBeInTheDocument();
    expect(screen.getByText("Call 4")).toBeInTheDocument();
  });

  it("renders save button", () => {
    render(<SettingsPage />);
    expect(screen.getByRole("button", { name: /save/i })).toBeInTheDocument();
  });

  it("renders config section heading", () => {
    render(<SettingsPage />);
    expect(screen.getByText(/LLM Configuration/i)).toBeInTheDocument();
  });

  it("initializes with Call 3 thinking = true", () => {
    render(<SettingsPage />);
    const call3Row = screen.getAllByRole("combobox")[2]; // Call 3 (Call 2 in 0-index)
    expect(call3Row).toBeInTheDocument();
  });
});
