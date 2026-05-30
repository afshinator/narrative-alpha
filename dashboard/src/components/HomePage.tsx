import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import type { ClusterSummary } from "../types";
import { fetchReports } from "../api";

export function HomePage() {
  const [reports, setReports] = useState<ClusterSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchReports()
      .then(setReports)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="page"><p className="loading">Loading reports…</p></div>;
  if (error) return <div className="page"><p className="error">Error: {error}</p></div>;
  if (reports.length === 0) return <div className="page"><p className="empty">No reports yet. Run a pipeline to get started.</p></div>;

  return (
    <div className="page">
      <h1 className="page-title">Forensic Reports</h1>
      <div className="report-list">
        {reports.map((r) => (
          <Link key={r.cluster_id} to={`/event/${r.cluster_id}`} className="report-card">
            <h2>{r.search_query}</h2>
            <p className="report-meta">{r.industry_vertical} · {r.corpus_count} articles · {r.timestamp_utc}</p>
          </Link>
        ))}
      </div>
    </div>
  );
}
