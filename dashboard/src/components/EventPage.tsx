import "@aejkatappaja/phantom-ui";

export function EventPage() {
  return (
    <div>
      <div className="no-backend-banner">
        <strong>No backend connected</strong>
        <span className="no-backend-hint">
          Run <code>uvicorn narrative.server:app --reload</code> and refresh.
        </span>
      </div>

      <div className="page">
        <h1 className="page-title">cluster-id</h1>
        <p className="page-subtitle">search query placeholder text</p>

        {/* Zone 1 */}
        <div className="zone">
          <div className="zone-header">
            <svg className="icon" viewBox="0 0 24 24" fill="none" stroke="#4ade80" strokeWidth="2">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
            </svg>
            <span className="zone-label">Zone 1 — Consensus truth baseline</span>
          </div>
          <div className="zone-body">
            <phantom-ui loading={true} animation="shimmer" reveal={0.3}>
              <div className="consensus-summary">
                Representative paragraph of consensus summary text that gives the skeleton its proper two-to-three-line layout shape for accurate shimmer block generation.
              </div>
              <div className="verified-badge">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" width="12" height="12">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                Authority Name (Ref: REF-001) — VERIFIED
              </div>
              <div className="anchor-nodes">
                <span className="node-pill">Anchor node one</span>
                <span className="node-pill">Anchor node two</span>
                <span className="node-pill">Anchor node three</span>
                <span className="node-pill">Anchor node four</span>
              </div>
            </phantom-ui>
          </div>
        </div>

        {/* Zone 2 */}
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
            <phantom-ui loading={true} animation="shimmer" stagger={0.04} reveal={0.3}>
              <table className="distortion-table">
                <thead data-shimmer-ignore>
                  <tr>
                    <th style={{ width: "26%" }}>Outlet vector</th>
                    <th style={{ width: "13%" }}>Omission (Oᵢ)</th>
                    <th style={{ width: "13%" }}>Volatility (Vf)</th>
                    <th style={{ width: "48%" }}>Detected text camouflage</th>
                  </tr>
                </thead>
                <tbody>
                  <tr>
                    <td><div className="outlet-name">News Source A</div><div className="outlet-domain">source-a.example.com</div></td>
                    <td><span className="badge badge-high">0.42 HIGH</span></td>
                    <td><span className="badge badge-med">0.35 MED</span></td>
                    <td className="camouflage"><span className="cam-raw">example phrasing</span><span className="cam-arrow"> → </span><span className="cam-clean">neutral term</span></td>
                  </tr>
                  <tr>
                    <td><div className="outlet-name">News Source B</div><div className="outlet-domain">source-b.example.com</div></td>
                    <td><span className="badge badge-med">0.28 MED</span></td>
                    <td><span className="badge badge-low">0.12 LOW</span></td>
                    <td className="camouflage" />
                  </tr>
                </tbody>
              </table>

              <div className="sub-header" data-shimmer-ignore>Narrative regime shifts</div>
              <div className="regime-card">
                <div className="regime-shift">
                  <span className="term-old">previous terminology</span>
                  <span className="term-arrow"> → </span>
                  <span className="term-new">replacement terminology</span>
                </div>
                <div className="regime-meta">
                  <span className="badge badge-high">HIGH sync</span>
                  <span>3 of 7 sources</span>
                  <span>synchronization score: 0.72</span>
                </div>
                <div className="regime-note">Interpretive note describing the detected terminology shift across sources.</div>
              </div>
            </phantom-ui>
          </div>
        </div>

        {/* Zone 3 */}
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
            <phantom-ui loading={true} animation="shimmer" stagger={0.03} reveal={0.3}>

              <div className="rep-warning">
                <div className="rep-warning-title">
                  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" width="13" height="13">
                    <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                    <line x1="12" y1="9" x2="12" y2="13" />
                    <line x1="12" y1="17" x2="12.01" y2="17" />
                  </svg>
                  Reputation alert: high scatter-shot ratio — Outlet Name
                </div>
                <div className="rep-warning-body">Warning message text describing the reputation concern with this outlet.</div>
              </div>

              <div className="sub-header" data-shimmer-ignore>Predictive narrative watch — outlier signals</div>
              <div className="outlier-card">
                <div className="outlier-claim">Outlier claim text that describes a detected narrative signal requiring monitoring and validation tracking over time.</div>
                <div className="outlier-meta">
                  <div className="meta-row"><span className="meta-label">Origin: </span><span className="meta-val">Outlet Name</span></div>
                  <div className="meta-row"><span className="meta-label">Validation rate: </span><span className="meta-val">40%</span></div>
                  <div className="meta-row" style={{ gridColumn: "1 / -1", marginTop: 5 }}>
                    <span className="meta-label">Status: </span>
                    <span className="pending-badge">PENDING · 30-day convergence window active</span>
                  </div>
                </div>
              </div>

              <div className="sub-header" data-shimmer-ignore>Reality divergence zones</div>
              <div className="divergence-block">
                <div className="div-topic">Divergence zone topic text for skeleton layout</div>
                <div className="div-status-row">
                  <span className="status-pill status-low">Consensus stability: MED (0.55)</span>
                  <span className="status-pill status-unresolved">Institutional convergence: CONTESTED</span>
                </div>
                <div className="narrative-list">
                  <div className="narrative-item">
                    <span className="narrative-name">Narrative structure description</span>
                    <div className="narrative-outlets">
                      <span className="outlet-tag">outlet-a.example.com</span>
                      <span className="outlet-tag">outlet-b.example.com</span>
                    </div>
                  </div>
                </div>
              </div>

              <div className="sub-header" data-shimmer-ignore>Reality fractures</div>
              <div className="fracture-card">
                <div className="fracture-header">
                  <span>FR-001 · Fracture topic example</span>
                  <span>MUTUALLY_EXCLUSIVE · UNRESOLVED</span>
                </div>
                <div className="fracture-body">
                  <div className="claim-block">
                    <div className="claim-label">Claim A</div>
                    <div className="claim-text">Claim A statement text describing first position with enough content for natural layout sizing in the skeleton.</div>
                    <div className="claim-outlets"><span className="outlet-tag">outlet-x.com</span></div>
                  </div>
                  <div className="claim-block">
                    <div className="claim-label">Claim B</div>
                    <div className="claim-text">Claim B statement text describing second position that fills the opposite column with representative length.</div>
                    <div className="claim-outlets"><span className="outlet-tag">outlet-y.com</span></div>
                  </div>
                </div>
                <div className="fracture-footer">
                  <span>No winner declared — incompatibility surfaced only</span>
                  <span>Classification method: LLM_SYNTHESIS</span>
                </div>
              </div>

            </phantom-ui>
          </div>
        </div>
      </div>
    </div>
  );
}
