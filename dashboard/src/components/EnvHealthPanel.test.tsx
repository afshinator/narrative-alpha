import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

vi.mock("../api", async (importOriginal) => {
  const actual = await importOriginal<typeof import("../api")>();
  return { ...actual, fetchEnvHealth: vi.fn() };
});

import { fetchEnvHealth } from "../api";
import { EnvHealthPanel } from "./EnvHealthPanel";

beforeEach(() => { vi.clearAllMocks(); });

describe("EnvHealthPanel — loading", () => {
  it("shows loading state initially", () => {
    vi.mocked(fetchEnvHealth).mockReturnValue(new Promise(() => {}));
    render(<EnvHealthPanel />);
    expect(screen.getByText(/Checking environment/i)).toBeTruthy();
  });
});

describe("EnvHealthPanel — all present", () => {
  it("renders present vars with check indicator", async () => {
    vi.mocked(fetchEnvHealth).mockResolvedValueOnce({
      status: "ok", detail: "All required vars set",
      present: ["DEEPSEEK_API_KEY", "OPENAI_API_KEY"], missing: [],
    });
    render(<EnvHealthPanel />);
    expect(await screen.findByText("DEEPSEEK_API_KEY")).toBeTruthy();
    expect(await screen.findByText("OPENAI_API_KEY")).toBeTruthy();
    expect(await screen.findByText(/All required variables are set/i)).toBeTruthy();
  });

  it("does not render any missing-var items when all present", async () => {
    vi.mocked(fetchEnvHealth).mockResolvedValueOnce({
      status: "ok", detail: "All required vars set",
      present: ["DEEPSEEK_API_KEY"], missing: [],
    });
    render(<EnvHealthPanel />);
    await screen.findByText("DEEPSEEK_API_KEY");
    expect(document.querySelectorAll(".env-var--missing").length).toBe(0);
  });
});

describe("EnvHealthPanel — degraded", () => {
  it("renders missing vars with hint text", async () => {
    vi.mocked(fetchEnvHealth).mockResolvedValueOnce({
      status: "degraded", detail: "Missing: OPENAI_API_KEY",
      present: ["DEEPSEEK_API_KEY"], missing: ["OPENAI_API_KEY"],
    });
    render(<EnvHealthPanel />);
    expect(await screen.findByText("OPENAI_API_KEY")).toBeTruthy();
    expect(await screen.findByText(/Not set — add to .env/i)).toBeTruthy();
  });

  it("does not show all-ok message when status is degraded", async () => {
    vi.mocked(fetchEnvHealth).mockResolvedValueOnce({
      status: "degraded", detail: "Missing: OPENAI_API_KEY",
      present: ["DEEPSEEK_API_KEY"], missing: ["OPENAI_API_KEY"],
    });
    render(<EnvHealthPanel />);
    await screen.findByText("OPENAI_API_KEY");
    expect(screen.queryByText(/All required variables are set/i)).toBeNull();
  });
});

describe("EnvHealthPanel — error", () => {
  it("shows error message when fetch fails", async () => {
    vi.mocked(fetchEnvHealth).mockRejectedValueOnce(new Error("Network error"));
    render(<EnvHealthPanel />);
    expect(await screen.findByText(/Could not load env status/i)).toBeTruthy();
    expect(await screen.findByText(/Network error/i)).toBeTruthy();
  });
});

describe("EnvHealthPanel — recheck", () => {
  it("re-fetches when Recheck is clicked", async () => {
    vi.mocked(fetchEnvHealth)
      .mockResolvedValueOnce({ status: "ok", detail: "", present: ["DEEPSEEK_API_KEY"], missing: [] })
      .mockResolvedValueOnce({ status: "ok", detail: "", present: ["DEEPSEEK_API_KEY", "OPENAI_API_KEY"], missing: [] });
    render(<EnvHealthPanel />);
    await screen.findByText("DEEPSEEK_API_KEY");
    await userEvent.click(screen.getByRole("button", { name: /Recheck/i }));
    expect(await screen.findByText("OPENAI_API_KEY")).toBeTruthy();
    expect(fetchEnvHealth).toHaveBeenCalledTimes(2);
  });
});
