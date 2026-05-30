import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { EventPage } from "./EventPage";

beforeEach(() => {
  vi.restoreAllMocks();
});

it("shows loading state initially", () => {
  vi.spyOn(globalThis, "fetch").mockReturnValue(new Promise(() => {}));
  render(
    <MemoryRouter initialEntries={["/event/EVT-001"]}>
      <Routes>
        <Route path="/event/:clusterId" element={<EventPage />} />
      </Routes>
    </MemoryRouter>
  );
  expect(screen.getByText("Loading report…")).toBeTruthy();
});

it("shows error message on fetch failure", async () => {
  vi.spyOn(globalThis, "fetch").mockRejectedValueOnce(new Error("Not found"));
  render(
    <MemoryRouter initialEntries={["/event/EVT-001"]}>
      <Routes>
        <Route path="/event/:clusterId" element={<EventPage />} />
      </Routes>
    </MemoryRouter>
  );
  expect(await screen.findByText(/Not found/)).toBeTruthy();
});

it("renders report from API data", async () => {
  const fakeReport = {
    event_meta: { cluster_id: "EVT-001", search_query: "Fab 7 halt", industry_vertical: "TECH", timestamp_utc: "now", corpus_count: 7, corpus_capped: false },
    consensus_reality_graph: { consensus_summary: "Things happened", verified_anchor_nodes: ["Fab 7"], primary_verifications: [] },
    distortion_matrix: [],
    outlier_signals: [],
    reputation_warnings: [],
    reality_divergence_zones: [],
    reality_fractures: [],
    narrative_regime_shifts: [],
  };
  vi.spyOn(globalThis, "fetch").mockResolvedValueOnce({ ok: true, json: () => Promise.resolve(fakeReport) } as Response);
  render(
    <MemoryRouter initialEntries={["/event/EVT-001"]}>
      <Routes>
        <Route path="/event/:clusterId" element={<EventPage />} />
      </Routes>
    </MemoryRouter>
  );
  expect(await screen.findByText("EVT-001")).toBeTruthy();
  expect(screen.getByText("Fab 7 halt")).toBeTruthy();
});
