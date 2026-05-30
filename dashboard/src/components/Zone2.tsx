import type { ForensicReport } from "../types";
import { Badge } from "./Badge";

interface Zone2Props {
  report: ForensicReport;
}

export function Zone2({ report }: Zone2Props) {
  const { distortion_matrix, narrative_regime_shifts } = report;

  return (
    <div className="zone">
      <div className="zone-header">
        <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
          <rect x="3" y="3" width="18" height="18" rx="2" />
          <line x1="3" y1="9" x2="21" y2="9" />
          <line x1="3" y1="15" x2="21" y2="15" />
          <line x1="9" y1="9" x2="9" y2="21" />
        </svg>
        <span className="zone-label">Zone 2 — Media distortion matrix</span>
      </div>
      <div className="zone-body">
        <table className="distortion-table">
          <thead>
            <tr>
              <th style={{ width: "26%" }}>Outlet vector</th>
              <th style={{ width: "13%" }}>Omission (Oᵢ)</th>
              <th style={{ width: "13%" }}>Volatility (Vf)</th>
              <th style={{ width: "48%" }}>Detected text camouflage</th>
            </tr>
          </thead>
          <tbody>
            {distortion_matrix.map((entry) => (
              <tr key={entry.source_domain}>
                <td>
                  <div className="outlet-name">{entry.outlet_name}</div>
                  <div className="outlet-domain">{entry.source_domain}</div>
                </td>
                <td>
                  <Badge level={entry.omission_label} label={`${entry.omission_index.toFixed(2)} ${entry.omission_label}`} />
                </td>
                <td>
                  <Badge level={entry.framing_volatility_label} label={`${entry.framing_volatility_score.toFixed(2)} ${entry.framing_volatility_label}`} />
                </td>
                <td className="camouflage">
                  {entry.linguistic_camouflage.map((cam, i) => (
                    <div key={i}>
                      <span className="cam-raw">{cam.raw_expression}</span>
                      <span className="cam-arrow"> → </span>
                      <span className="cam-clean">{cam.clinical_translation}</span>
                    </div>
                  ))}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {narrative_regime_shifts.length > 0 && (
          <>
            <div className="sub-header">Narrative regime shifts</div>
            {narrative_regime_shifts.map((shift) => (
              <div key={shift.shift_id} className="regime-card">
                <div className="regime-shift">
                  <span className="term-old">{shift.detected_shift.previous_term}</span>
                  <span className="term-arrow"> → </span>
                  <span className="term-new">{shift.detected_shift.replacement_term}</span>
                </div>
                <div className="regime-meta">
                  <Badge level={shift.synchronization_label} label={`${shift.synchronization_label} sync`} />
                  <span>{shift.observed_across} of {shift.total_sources} sources</span>
                  <span>synchronization score: {shift.synchronization_score.toFixed(2)}</span>
                </div>
                <div className="regime-note">{shift.interpretive_note}</div>
              </div>
            ))}
          </>
        )}
      </div>
    </div>
  );
}
