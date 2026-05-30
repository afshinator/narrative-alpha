import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Zone1 } from "./Zone1";
import type { ForensicReport } from "../types";

const baseReport = {
  event_meta: {
    cluster_id: "EVT-001",
    search_query: "test",
    industry_vertical: "TECHNOLOGY",
    timestamp_utc: "2026-05-28T02:00:00Z",
    corpus_count: 7,
    corpus_capped: false,
  },
  consensus_reality_graph: {
    consensus_summary: "Test consensus summary text.",
    verified_anchor_nodes: ["Fab 7", "Operations halted"],
    primary_verifications: [
      { authority: "Energy Filing", reference_id: "REG-001", status: "VERIFIED" },
    ],
  },
  distortion_matrix: [],
  outlier_signals: [],
  reputation_warnings: [],
  reality_divergence_zones: [],
  reality_fractures: [],
  narrative_regime_shifts: [],
} satisfies ForensicReport;

describe("Zone1", () => {
  it("renders consensus summary text", () => {
    render(<Zone1 report={baseReport} />);
    expect(screen.getByText("Test consensus summary text.")).toBeInTheDocument();
  });

  it("renders verified anchor node pills", () => {
    render(<Zone1 report={baseReport} />);
    expect(screen.getByText("Fab 7")).toBeInTheDocument();
    expect(screen.getByText("Operations halted")).toBeInTheDocument();
  });

  it("renders primary verification badge", () => {
    render(<Zone1 report={baseReport} />);
    expect(screen.getByText(/Energy Filing/)).toBeInTheDocument();
    expect(screen.getByText(/REG-001/)).toBeInTheDocument();
  });

  it("shows corpus-capped indicator when corpus_capped is true", () => {
    const capped = {
      ...baseReport,
      event_meta: { ...baseReport.event_meta, corpus_capped: true },
    };
    render(<Zone1 report={capped} />);
    expect(screen.getByText(/capped/i)).toBeInTheDocument();
  });

  it("hides corpus-capped indicator when corpus_capped is false", () => {
    render(<Zone1 report={baseReport} />);
    expect(screen.queryByText(/capped/i)).not.toBeInTheDocument();
  });
});
