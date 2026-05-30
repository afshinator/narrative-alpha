import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { SettingsRow } from "./SettingsRow";

const defaultProps = {
  slotName: "Call 1",
  slotDescription: "Entity normalization",
  provider: "deepseek",
  model: "deepseek-v4-flash",
  thinking: false,
  temperature: 0.1,
  onUpdate: () => {},
};

describe("SettingsRow", () => {
  it("renders slot name and description", () => {
    render(<SettingsRow {...defaultProps} />);
    expect(screen.getByText("Call 1")).toBeInTheDocument();
    expect(screen.getByText("Entity normalization")).toBeInTheDocument();
  });

  it("renders provider select with current value", () => {
    render(<SettingsRow {...defaultProps} />);
    const select = screen.getByRole("combobox") as HTMLSelectElement;
    expect(select.value).toBe("deepseek");
  });

  it("renders model input with current value", () => {
    render(<SettingsRow {...defaultProps} />);
    const input = screen.getByDisplayValue("deepseek-v4-flash") as HTMLInputElement;
    expect(input).toBeInTheDocument();
  });

  it("shows thinking checkbox for deepseek provider", () => {
    render(<SettingsRow {...defaultProps} />);
    const checkboxes = document.querySelectorAll('.thinking-toggle input[type="checkbox"]');
    expect(checkboxes.length).toBe(1);
  });

  it("shows N/A text instead of checkbox for non-deepseek provider", () => {
    render(
      <SettingsRow {...defaultProps} provider="openai" thinking={false} />
    );
    expect(screen.getByText("N/A")).toBeInTheDocument();
  });

  it("renders temperature slider", () => {
    render(<SettingsRow {...defaultProps} />);
    const slider = document.querySelector('input[type="range"]');
    expect(slider).toBeInTheDocument();
  });
});
