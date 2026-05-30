import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Zone2 } from "./Zone2";
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
    consensus_summary: "",
    verified_anchor_nodes: [],
    primary_verifications: [],
  },
  distortion_matrix: [
    {
      outlet_name: "Outlet A",
      source_domain: "outleta.com",
      omission_index: 0.65,
      omission_label: "HIGH",
      framing_volatility_score: 0.12,
      framing_volatility_label: "LOW",
      identifiable_omissions: ["Detail X"],
      linguistic_camouflage: [
        {
          raw_expression: "minor issue",
          clinical_translation: "major failure",
        },
      ],
    },
  ],
  outlier_signals: [],
  reputation_warnings: [],
  reality_divergence_zones: [],
  reality_fractures: [],
  narrative_regime_shifts: [
    {
      shift_id: "RS-001",
      topic: "Terminology shift",
      detected_shift: {
        previous_term: "power outage",
        replacement_term: "service interruption",
      },
      observed_across: 6,
      total_sources: 8,
      synchronization_score: 0.75,
      synchronization_label: "HIGH",
      interpretive_note: "Language shifted.",
    },
  ],
} satisfies ForensicReport;

describe("Zone2", () => {
  it("renders outlet name and domain in table", () => {
    render(<Zone2 report={baseReport} />);
    expect(screen.getByText("Outlet A")).toBeInTheDocument();
    expect(screen.getByText("outleta.com")).toBeInTheDocument();
  });

  it("renders Oi badge for each entry", () => {
    render(<Zone2 report={baseReport} />);
    const badges = screen.getAllByText(/0\.65|0\.12/);
    expect(badges.length).toBeGreaterThan(0);
  });

  it("renders camouflage pair text", () => {
    render(<Zone2 report={baseReport} />);
    expect(screen.getByText("minor issue")).toBeInTheDocument();
    expect(screen.getByText("major failure")).toBeInTheDocument();
  });

  it("shows regime shift card with term migration", () => {
    render(<Zone2 report={baseReport} />);
    expect(screen.getByText("power outage")).toBeInTheDocument();
    expect(screen.getByText("service interruption")).toBeInTheDocument();
  });

  it("shows synchronization score in regime card", () => {
    render(<Zone2 report={baseReport} />);
    expect(screen.getByText(/0.75/)).toBeInTheDocument();
  });

  it("shows regime interpretive note", () => {
    render(<Zone2 report={baseReport} />);
    expect(screen.getByText(/Language shifted/)).toBeInTheDocument();
  });

  it("hides regime shifts panel when empty", () => {
    const noShifts = {
      ...baseReport,
      narrative_regime_shifts: [],
    };
    render(<Zone2 report={noShifts} />);
    expect(screen.queryByText(/Regime/)).not.toBeInTheDocument();
  });
});
