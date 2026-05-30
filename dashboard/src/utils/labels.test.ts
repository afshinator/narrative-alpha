import { describe, it, expect } from "vitest";
import {
  omissionLabel,
  scatterShotLabel,
  consensusStabilityLabel,
  consensusStabilityClass,
  convergenceStatusClass,
  formatTimestamp,
  synchronizationLabel,
  synchronizationClass,
} from "./labels";

describe("omissionLabel", () => {
  it('returns "LOW" for oi < 0.25', () => {
    expect(omissionLabel(0)).toBe("LOW");
    expect(omissionLabel(0.1)).toBe("LOW");
    expect(omissionLabel(0.24)).toBe("LOW");
  });

  it('returns "MED" for 0.25 <= oi < 0.50', () => {
    expect(omissionLabel(0.25)).toBe("MED");
    expect(omissionLabel(0.3)).toBe("MED");
    expect(omissionLabel(0.49)).toBe("MED");
  });

  it('returns "HIGH" for oi >= 0.50', () => {
    expect(omissionLabel(0.5)).toBe("HIGH");
    expect(omissionLabel(0.75)).toBe("HIGH");
    expect(omissionLabel(1.0)).toBe("HIGH");
  });
});

describe("scatterShotLabel", () => {
  it('returns "LOW" for sa < 0.35', () => {
    expect(scatterShotLabel(0)).toBe("LOW");
    expect(scatterShotLabel(0.2)).toBe("LOW");
    expect(scatterShotLabel(0.34)).toBe("LOW");
  });

  it('returns "MED" for 0.35 <= sa < 0.60', () => {
    expect(scatterShotLabel(0.35)).toBe("MED");
    expect(scatterShotLabel(0.5)).toBe("MED");
    expect(scatterShotLabel(0.59)).toBe("MED");
  });

  it('returns "HIGH" for sa >= 0.60', () => {
    expect(scatterShotLabel(0.6)).toBe("HIGH");
    expect(scatterShotLabel(0.8)).toBe("HIGH");
    expect(scatterShotLabel(1.0)).toBe("HIGH");
  });
});

describe("consensusStabilityLabel", () => {
  it('returns "HIGH" for score >= 0.75', () => {
    expect(consensusStabilityLabel(0.75)).toBe("HIGH");
    expect(consensusStabilityLabel(0.9)).toBe("HIGH");
    expect(consensusStabilityLabel(1.0)).toBe("HIGH");
  });

  it('returns "MED" for 0.40 <= score < 0.75', () => {
    expect(consensusStabilityLabel(0.4)).toBe("MED");
    expect(consensusStabilityLabel(0.6)).toBe("MED");
    expect(consensusStabilityLabel(0.74)).toBe("MED");
  });

  it('returns "LOW" for score < 0.40', () => {
    expect(consensusStabilityLabel(0)).toBe("LOW");
    expect(consensusStabilityLabel(0.2)).toBe("LOW");
    expect(consensusStabilityLabel(0.39)).toBe("LOW");
  });
});

describe("consensusStabilityClass", () => {
  it('returns "status-high" for HIGH', () => {
    expect(consensusStabilityClass("HIGH")).toBe("status-high");
  });

  it('returns "status-med" for MED', () => {
    expect(consensusStabilityClass("MED")).toBe("status-med");
  });

  it('returns "status-low" for LOW', () => {
    expect(consensusStabilityClass("LOW")).toBe("status-low");
  });
});

describe("convergenceStatusClass", () => {
  it('returns "status-resolved" for RESOLVED', () => {
    expect(convergenceStatusClass("RESOLVED")).toBe("status-resolved");
  });

  it('returns "status-contested" for CONTESTED', () => {
    expect(convergenceStatusClass("CONTESTED")).toBe("status-contested");
  });

  it('returns "status-unresolved" for UNRESOLVED', () => {
    expect(convergenceStatusClass("UNRESOLVED")).toBe("status-unresolved");
  });

  it('defaults to "status-unresolved" for unknown status', () => {
    expect(convergenceStatusClass("UNKNOWN")).toBe("status-unresolved");
  });
});

describe("synchronizationLabel", () => {
  it('returns "HIGH" for score >= 0.70', () => {
    expect(synchronizationLabel(0.7)).toBe("HIGH");
    expect(synchronizationLabel(0.85)).toBe("HIGH");
    expect(synchronizationLabel(1.0)).toBe("HIGH");
  });

  it('returns "MED" for 0.40 <= score < 0.70', () => {
    expect(synchronizationLabel(0.4)).toBe("MED");
    expect(synchronizationLabel(0.55)).toBe("MED");
    expect(synchronizationLabel(0.69)).toBe("MED");
  });

  it('returns "LOW" for score < 0.40', () => {
    expect(synchronizationLabel(0)).toBe("LOW");
    expect(synchronizationLabel(0.2)).toBe("LOW");
    expect(synchronizationLabel(0.39)).toBe("LOW");
  });
});

describe("synchronizationClass", () => {
  it('returns "badge badge-high" for HIGH', () => {
    expect(synchronizationClass("HIGH")).toBe("badge badge-high");
  });

  it('returns "badge badge-med" for MED', () => {
    expect(synchronizationClass("MED")).toBe("badge badge-med");
  });

  it('returns "badge badge-low" for LOW', () => {
    expect(synchronizationClass("LOW")).toBe("badge badge-low");
  });
});

describe("formatTimestamp", () => {
  it("formats ISO timestamp to short date + time", () => {
    expect(formatTimestamp("2026-05-28T02:00:00Z")).toBe("2026-05-28 02:00");
  });

  it("returns empty string for null", () => {
    expect(formatTimestamp(null)).toBe("");
  });

  it("returns empty string for undefined", () => {
    expect(formatTimestamp(undefined)).toBe("");
  });
});
