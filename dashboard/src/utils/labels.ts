export function omissionLabel(oi: number): string {
  if (oi < 0.25) return "LOW";
  if (oi < 0.50) return "MED";
  return "HIGH";
}

export function scatterShotLabel(sa: number): string {
  if (sa < 0.35) return "LOW";
  if (sa < 0.60) return "MED";
  return "HIGH";
}

export function consensusStabilityLabel(score: number): string {
  if (score >= 0.75) return "HIGH";
  if (score >= 0.40) return "MED";
  return "LOW";
}

export function consensusStabilityClass(label: string): string {
  const map: Record<string, string> = {
    HIGH: "status-high",
    MED: "status-med",
    LOW: "status-low",
  };
  return map[label] ?? "status-low";
}

export function convergenceStatusClass(status: string): string {
  const map: Record<string, string> = {
    RESOLVED: "status-resolved",
    CONTESTED: "status-contested",
    UNRESOLVED: "status-unresolved",
  };
  return map[status] ?? "status-unresolved";
}

export function synchronizationLabel(score: number): string {
  if (score >= 0.70) return "HIGH";
  if (score >= 0.40) return "MED";
  return "LOW";
}

export function synchronizationClass(label: string): string {
  const map: Record<string, string> = {
    HIGH: "badge badge-high",
    MED: "badge badge-med",
    LOW: "badge badge-low",
  };
  return map[label] ?? "badge badge-low";
}

export function formatTimestamp(ts: string | null | undefined): string {
  if (ts == null) return "";
  const date = new Date(ts);
  if (isNaN(date.getTime())) return "";
  const y = date.getUTCFullYear();
  const m = String(date.getUTCMonth() + 1).padStart(2, "0");
  const d = String(date.getUTCDate()).padStart(2, "0");
  const hh = String(date.getUTCHours()).padStart(2, "0");
  const mm = String(date.getUTCMinutes()).padStart(2, "0");
  return `${y}-${m}-${d} ${hh}:${mm}`;
}
