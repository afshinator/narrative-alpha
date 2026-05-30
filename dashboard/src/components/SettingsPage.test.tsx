import { it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { SettingsPage } from "./SettingsPage";

// vi.mock is hoisted — factory must not reference outer variables
vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  const cfg = {
    call_1_entity_normalization: { provider: "deepseek", model: "deepseek-v4-flash", thinking: false, temperature: 0.1 },
    call_2_linguistic_neutralization: { provider: "deepseek", model: "deepseek-v4-flash", thinking: false, temperature: 0.1 },
    call_3_graph_extraction: { provider: "deepseek", model: "deepseek-v4-pro", thinking: true, temperature: 0.1 },
    call_4_forensic_synthesis: { provider: "deepseek", model: "deepseek-v4-pro", thinking: true, temperature: 0.1 },
  };
  const env = {
    status: "ok" as const,
    detail: "All required vars set",
    present: ["DEEPSEEK_API_KEY", "OPENAI_API_KEY", "BRIGHTDATA_API_KEY", "BRIGHTDATA_SERP_ZONE", "BRIGHTDATA_UNLOCKER_ZONE"],
    missing: [],
  };
  return {
    ...actual,
    fetchConfig: vi.fn().mockResolvedValue(cfg),
    saveConfig: vi.fn().mockResolvedValue({ status: "ok", config: cfg }),
    fetchEnvHealth: vi.fn().mockResolvedValue(env),
  };
});

import { fetchConfig, fetchEnvHealth } from "../api";

const fakeConfig = {
  call_1_entity_normalization: { provider: "deepseek", model: "deepseek-v4-flash", thinking: false, temperature: 0.1 },
  call_2_linguistic_neutralization: { provider: "deepseek", model: "deepseek-v4-flash", thinking: false, temperature: 0.1 },
  call_3_graph_extraction: { provider: "deepseek", model: "deepseek-v4-pro", thinking: true, temperature: 0.1 },
  call_4_forensic_synthesis: { provider: "deepseek", model: "deepseek-v4-pro", thinking: true, temperature: 0.1 },
};

const fakeEnvHealth = {
  status: "ok" as const,
  detail: "All required vars set",
  present: ["DEEPSEEK_API_KEY", "OPENAI_API_KEY", "BRIGHTDATA_API_KEY", "BRIGHTDATA_SERP_ZONE", "BRIGHTDATA_UNLOCKER_ZONE"],
  missing: [],
};

beforeEach(() => {
  vi.clearAllMocks();
  vi.mocked(fetchConfig).mockResolvedValue(fakeConfig);
  vi.mocked(fetchEnvHealth).mockResolvedValue(fakeEnvHealth);
});

it("shows loading state initially", () => {
  vi.mocked(fetchConfig).mockReturnValueOnce(new Promise(() => {}));
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  expect(screen.getByText("Loading config…")).toBeTruthy();
});

it("renders settings rows after fetch", async () => {
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  expect(await screen.findByText("Call 1")).toBeTruthy();
  expect(await screen.findByText("Call 4")).toBeTruthy();
});

it("renders save button after fetch", async () => {
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  expect(await screen.findByText("Save Configuration")).toBeTruthy();
});

it("renders EnvHealthPanel with env var status", async () => {
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  expect(await screen.findByText("Environment Variables")).toBeTruthy();
});

it("shows error message when fetch fails", async () => {
  vi.mocked(fetchConfig).mockRejectedValueOnce(new Error("Failed to load config"));
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  expect(await screen.findByText(/Failed to load config/)).toBeTruthy();
});

it("hides save button when config failed to load", async () => {
  vi.mocked(fetchConfig).mockRejectedValueOnce(new Error("Network error"));
  render(<MemoryRouter><SettingsPage /></MemoryRouter>);
  await screen.findByText(/Network error/);
  expect(screen.queryByText("Save Configuration")).toBeNull();
});
