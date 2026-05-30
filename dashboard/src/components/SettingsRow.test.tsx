import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SettingsRow } from "./SettingsRow";

const defaultProps = {
  slotName: "Call 1",
  slotDescription: "Entity normalization",
  model: "deepseek-v4-flash",
  onChange: vi.fn(),
};

describe("SettingsRow", () => {
  it("renders slot name and description", () => {
    render(<SettingsRow {...defaultProps} />);
    expect(screen.getByText("Call 1")).toBeInTheDocument();
    expect(screen.getByText("Entity normalization")).toBeInTheDocument();
  });

  it("renders model input with current value", () => {
    render(<SettingsRow {...defaultProps} />);
    expect(screen.getByDisplayValue("deepseek-v4-flash")).toBeInTheDocument();
  });

  it("calls onChange with new value when model input changes", () => {
    const onChange = vi.fn();
    render(<SettingsRow {...defaultProps} onChange={onChange} />);
    fireEvent.change(screen.getByDisplayValue("deepseek-v4-flash"), { target: { value: "deepseek-v4-pro" } });
    expect(onChange).toHaveBeenCalledWith("deepseek-v4-pro");
  });

  it("does not render a provider select", () => {
    render(<SettingsRow {...defaultProps} />);
    expect(screen.queryByRole("combobox")).toBeNull();
  });

  it("does not render a temperature range slider", () => {
    render(<SettingsRow {...defaultProps} />);
    expect(document.querySelector('input[type="range"]')).toBeNull();
  });

  it("does not render a thinking checkbox", () => {
    render(<SettingsRow {...defaultProps} />);
    expect(document.querySelector('input[type="checkbox"]')).toBeNull();
  });
});
