import type { ForensicReport } from "../types";
import { Pill } from "./Pill";

interface Zone1Props {
  report: ForensicReport;
}

export function Zone1({ report }: Zone1Props) {
  const { consensus_reality_graph: crg, event_meta } = report;

  return (
    <div className="zone">
      <div className="zone-header">
        <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="2">
          <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
        </svg>
        <span className="zone-label">Zone 1 — Consensus truth baseline</span>
        {event_meta.corpus_capped && (
          <span className="corpus-cap-badge">Corpus capped</span>
        )}
      </div>
      <div className="zone-body">
        <div className="consensus-summary">{crg.consensus_summary}</div>

        {crg.primary_verifications.map((pv) => (
          <div key={pv.reference_id} className="verified-badge">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="12" height="12">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            {pv.authority} (Ref: {pv.reference_id}) — {pv.status}
          </div>
        ))}

        <div className="anchor-nodes">
          {crg.verified_anchor_nodes.map((node) => (
            <Pill key={node}>{node}</Pill>
          ))}
        </div>
      </div>
    </div>
  );
}
