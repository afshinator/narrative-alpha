import type { ForensicReport } from "../types";
import { Badge } from "./Badge";

interface Zone3Props {
  report: ForensicReport;
}

export function Zone3({ report }: Zone3Props) {
  const {
    reputation_warnings,
    outlier_signals,
    reality_divergence_zones,
    reality_fractures,
  } = report;

  return (
    <div className="zone">
      <div className="zone-header">
        <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="11" cy="11" r="8" />
          <line x1="21" y1="21" x2="16.65" y2="16.65" />
          <line x1="11" y1="8" x2="11" y2="14" />
          <line x1="8" y1="11" x2="14" y2="11" />
        </svg>
        <span className="zone-label">Zone 3 — Forensic analysis of outlier signals</span>
      </div>
      <div className="zone-body">
        {reputation_warnings
          .filter((w) => w.warning_triggered)
          .map((w) => (
            <div key={w.source_domain} className="rep-warning">
              <div className="rep-warning-title">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="13" height="13">
                  <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
                Reputation alert: high scatter-shot ratio — {w.outlet_name}
              </div>
              <div className="rep-warning-meta">
                <span className="rep-warning-meta-item">
                  Scatter-shot factor: <strong>{(w.scatter_shot_anomaly_factor * 100).toFixed(0)}%</strong>
                </span>
                <span className="rep-warning-meta-item">
                  Label: <span className={`badge badge-${w.scatter_shot_label === "HIGH" ? "high" : w.scatter_shot_label === "MED" ? "med" : "low"}`}>{w.scatter_shot_label}</span>
                </span>
                <span className="rep-warning-meta-item">
                  Validation rate: <strong>{(w.historical_origin_validation_rate * 100).toFixed(0)}%</strong>
                </span>
                <span className="rep-warning-meta-item">
                  Domain: <strong>{w.source_domain}</strong>
                </span>
              </div>
              <div className="rep-warning-body">{w.warning_message}</div>
            </div>
          ))}

        <div className="sub-header">Predictive narrative watch — outlier signals</div>
        {outlier_signals.map((s) => (
          <div key={s.signal_id} className="outlier-card">
            <div className="outlier-claim">{s.extracted_claim}</div>
            <div className="outlier-meta">
              <div className="meta-row">
                <span className="meta-label">Origin: </span>
                <span className="meta-val">{s.origin_outlet}</span>
              </div>
              <div className="meta-row">
                <span className="meta-label">Validation rate: </span>
                <span className="meta-val">
                  {(s.outlier_origin_provenance.historical_origin_validation_rate * 100).toFixed(0)}%
                </span>
              </div>
              <div className="meta-row" style={{ gridColumn: "1 / -1", marginTop: 5 }}>
                <span className="meta-label">Status: </span>
                <span className="pending-badge">
                  {s.validation_tracking.current_state} · {s.validation_tracking.evaluation_window_days}-day convergence window active
                </span>
              </div>
            </div>
          </div>
        ))}

        {reality_divergence_zones.length > 0 && (
          <>
            <div className="sub-header">Reality divergence zones</div>
            {reality_divergence_zones.map((z, i) => (
              <div key={i} className="divergence-block">
                <div className="div-topic">{z.topic}</div>
                <div className="div-status-row">
                  <span className={`status-pill status-${z.consensus_stability.toLowerCase()}`}>
                    Consensus stability: {z.consensus_stability} ({z.consensus_stability_score.toFixed(2)})
                  </span>
                  <span className={`status-pill status-${z.institutional_convergence.toLowerCase()}`}>
                    Institutional convergence: {z.institutional_convergence}
                  </span>
                </div>
                <div className="narrative-list">
                  {z.observed_narrative_structures.map((narrative) => (
                    <div key={narrative} className="narrative-item">
                      <span className="narrative-name">{narrative}</span>
                      <div className="narrative-outlets">
                        {(z.supporting_outlets[narrative] || []).map((domain) => (
                          <span key={domain} className="outlet-tag">{domain}</span>
                        ))}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </>
        )}

        {reality_fractures.length > 0 && (
          <>
            <div className="sub-header">Reality fractures</div>
            {reality_fractures.map((f) => (
              <div key={f.fracture_id} className="fracture-card">
                <div className="fracture-header">
                  <span>{f.fracture_id} · {f.topic}</span>
                  <span>{f.relationship} · {f.resolution_status}</span>
                </div>
                <div className="fracture-body">
                  <div className="claim-block">
                    <div className="claim-label">Claim A</div>
                    <div className="claim-text">{f.claim_a.statement}</div>
                    <div className="claim-outlets">
                      {f.claim_a.supporting_outlets.map((d) => (
                        <span key={d} className="outlet-tag">{d}</span>
                      ))}
                    </div>
                  </div>
                  <div className="claim-block">
                    <div className="claim-label">Claim B</div>
                    <div className="claim-text">{f.claim_b.statement}</div>
                    <div className="claim-outlets">
                      {f.claim_b.supporting_outlets.map((d) => (
                        <span key={d} className="outlet-tag">{d}</span>
                      ))}
                    </div>
                  </div>
                </div>
                <div className="fracture-footer">
                  <span>No winner declared — incompatibility surfaced only</span>
                  <span>Classification method: {f.classification_method}</span>
                </div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
