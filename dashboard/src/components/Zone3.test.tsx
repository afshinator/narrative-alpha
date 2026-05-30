import { describe, it, expect } from "vitest";
import { render, screen } from "@testing-library/react";
import { Zone3 } from "./Zone3";
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
  distortion_matrix: [],
  outlier_signals: [
    {
      signal_id: "OS-1001",
      origin_outlet: "Test Insider",
      origin_domain: "testinsider.com",
      extracted_claim: "This is a test outlier claim.",
      timestamp_first_seen: "2026-05-28T04:30:00Z",
      outlier_origin_provenance: {
        classification: "SINGLE_SOURCE_ORIGIN",
        historical_origin_validation_rate: 0.84,
        scatter_shot_anomaly_factor: 0.72,
        scatter_shot_label: "HIGH",
        reputation_warning_triggered: true,
        echo_chamber_mimics: [],
      },
      validation_tracking: {
        current_state: "PENDING",
        last_checked_timestamp: "2026-05-28T04:30:00Z",
        consensus_absorption_status: "PENDING",
        evaluation_window_days: 30,
      },
    },
  ],
  reputation_warnings: [
    {
      outlet_name: "Test Insider",
      source_domain: "testinsider.com",
      warning_triggered: true,
      historical_origin_validation_rate: 0.84,
      scatter_shot_anomaly_factor: 0.72,
      scatter_shot_label: "HIGH",
      warning_message: "Test warning message.",
    },
  ],
  reality_divergence_zones: [
    {
      topic: "Cause of shutdown",
      consensus_stability: "LOW",
      consensus_stability_score: 0.21,
      institutional_convergence: "UNRESOLVED",
      observed_narrative_structures: ["Grid failure", "Cyber attack"],
      supporting_outlets: {
        "Grid failure": ["outleta.com"],
        "Cyber attack": ["testinsider.com"],
      },
    },
  ],
  reality_fractures: [
    {
      fracture_id: "RF-001",
      topic: "Root cause",
      claim_a: {
        statement: "Transformer overload.",
        supporting_outlets: ["outleta.com"],
      },
      claim_b: {
        statement: "Remote override.",
        supporting_outlets: ["testinsider.com"],
      },
      relationship: "STRUCTURALLY_CONTRADICTORY",
      resolution_status: "UNRESOLVED",
      classification_method: "LLM_ASSISTED",
    },
  ],
  narrative_regime_shifts: [],
} satisfies ForensicReport;

describe("Zone3", () => {
  it("renders reputation warning banner", () => {
    render(<Zone3 report={baseReport} />);
    expect(screen.getByText(/Test warning message/)).toBeInTheDocument();
  });

  it("renders scatter_shot_anomaly_factor and label in warning card", () => {
    render(<Zone3 report={baseReport} />);
    expect(screen.getByText(/72%/)).toBeInTheDocument();
    expect(screen.getByText("HIGH")).toBeInTheDocument();
  });

  it("renders historical_origin_validation_rate in warning card", () => {
    render(<Zone3 report={baseReport} />);
    const rates = screen.getAllByText(/84%/);
    expect(rates.length).toBe(2);
  });

  it("renders outlier signal claim text", () => {
    render(<Zone3 report={baseReport} />);
    expect(screen.getByText(/test outlier claim/)).toBeInTheDocument();
  });

  it("renders divergence zone topic", () => {
    render(<Zone3 report={baseReport} />);
    expect(screen.getByText("Cause of shutdown")).toBeInTheDocument();
  });

  it("renders divergence zone narrative structures", () => {
    render(<Zone3 report={baseReport} />);
    expect(screen.getByText("Grid failure")).toBeInTheDocument();
    expect(screen.getByText("Cyber attack")).toBeInTheDocument();
  });

  it("renders fracture claims", () => {
    render(<Zone3 report={baseReport} />);
    expect(screen.getByText(/Transformer overload/)).toBeInTheDocument();
    expect(screen.getByText(/Remote override/)).toBeInTheDocument();
  });

  it("renders classification method in fracture footer", () => {
    render(<Zone3 report={baseReport} />);
    expect(screen.getByText(/LLM_ASSISTED/)).toBeInTheDocument();
  });

  it("hides fracture section when empty", () => {
    const noFractures = { ...baseReport, reality_fractures: [] };
    render(<Zone3 report={noFractures} />);
    expect(screen.queryByText(/fracture/i)).not.toBeInTheDocument();
  });
});
