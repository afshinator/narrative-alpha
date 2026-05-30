import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import type { ClusterSummary } from "../types";
import { fetchReports } from "../api";
import { PipelineRunner } from "./PipelineRunner";

export function HomePage() {
  const [reports, setReports] = useState<ClusterSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState<string | null>(null);

  const loadReports = useCallback(() => {
    setLoading(true);
    setError(null);
    fetchReports()
      .then(setReports)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { loadReports(); }, [loadReports]);

  return (
    <div className="page">
      <PipelineRunner onComplete={loadReports} />

      {loading && <p className="loading">Loading reports…</p>}
      {error && <p className="error">Error: {error}</p>}
      {!loading && !error && reports.length === 0 && (
        <p className="empty">No reports yet. Run a pipeline to get started.</p>
      )}
      {!loading && !error && reports.length > 0 && (
        <>
          <h1 className="page-title">Forensic Reports</h1>
          <div className="report-list">
            {reports.map((r) => (
              <Link key={r.cluster_id} to={`/event/${r.cluster_id}`} className="report-card">
                <h2>{r.search_query}</h2>
                <p className="report-meta">{r.industry_vertical} · {r.corpus_count} articles · {r.timestamp_utc}</p>
              </Link>
            ))}
          </div>
        </>
      )}
    </div>
  );
}
