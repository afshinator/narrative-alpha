import { describe, it, expect, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { SettingsRow } from "./SettingsRow";

const defaultProps = {
  slotName: "Call 1",
  slotDescription: "Entity normalization",
  provider: "deepseek",
  model: "deepseek-v4-flash",
  onChange: vi.fn(),
  onProviderChange: vi.fn(),
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

  it("renders a provider select with the current provider selected", () => {
    render(<SettingsRow {...defaultProps} provider="groq" />);
    const select = screen.getByRole("combobox", { name: /provider for call 1/i });
    expect(select).toBeInTheDocument();
    expect((select as HTMLSelectElement).value).toBe("groq");
  });

  it("calls onProviderChange when provider select changes", () => {
    const onProviderChange = vi.fn();
    render(<SettingsRow {...defaultProps} onProviderChange={onProviderChange} />);
    const select = screen.getByRole("combobox", { name: /provider for call 1/i });
    fireEvent.change(select, { target: { value: "openai" } });
    expect(onProviderChange).toHaveBeenCalledWith("openai");
  });

  it("renders all four provider options", () => {
    render(<SettingsRow {...defaultProps} />);
    const select = screen.getByRole("combobox", { name: /provider for call 1/i });
    const options = Array.from((select as HTMLSelectElement).options).map((o) => o.value);
    expect(options).toEqual(expect.arrayContaining(["deepseek", "openai", "google", "groq"]));
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
