import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SettingsPage } from "./SettingsPage";

const fakeConfig = {
  call_1_entity_normalization: { provider: "deepseek", model: "deepseek-v4-flash", thinking: false, temperature: 0.1 },
  call_2_linguistic_neutralization: { provider: "deepseek", model: "deepseek-v4-flash", thinking: false, temperature: 0.1 },
  call_3_graph_extraction: { provider: "deepseek", model: "deepseek-v4-pro", thinking: true, temperature: 0.1 },
  call_4_forensic_synthesis: { provider: "deepseek", model: "deepseek-v4-pro", thinking: true, temperature: 0.1 },
};

beforeEach(() => {
  vi.restoreAllMocks();
});

it("shows loading state initially", () => {
  vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  expect(screen.getByText("Loading config…")).toBeTruthy();
});

it("renders settings rows after fetch", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(fakeConfig) } as Response);
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  expect(await screen.findByText("Call 1")).toBeTruthy();
  expect(await screen.findByText("Call 4")).toBeTruthy();
});

it("renders save button after fetch", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(fakeConfig) } as Response);
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  expect(await screen.findByText("Save Configuration")).toBeTruthy();
});

it("shows Call 3 thinking = true from backend", async () => {
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(fakeConfig) } as Response);
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  const onText = await screen.findAllByText("On");
  expect(onText.length).toBeGreaterThanOrEqual(2);
});

it("shows error message when fetch fails", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("Failed to load config"));
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  expect(await screen.findByText(/Failed to load config/)).toBeTruthy();
});

it("hides save button when config failed to load", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("Network error"));
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  await screen.findByText(/Network error/);
  expect(screen.queryByText("Save Configuration")).toBeNull();
});
