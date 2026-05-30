import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import { Zone1 } from "./Zone1";
import { Zone2 } from "./Zone2";
import { Zone3 } from "./Zone3";
import { fetchReport } from "../api";
import type { ForensicReport } from "../types";

export function EventPage() {
  const { clusterId } = useParams<{ clusterId: string }>();
  const [report, setReport] = useState<ForensicReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!clusterId) return;
    setLoading(true);
    setError(null);
    fetchReport(clusterId)
      .then(setReport)
      .catch((e: Error) => setError(e.message))
      .finally(() => setLoading(false));
  }, [clusterId]);

  if (loading) return <div className="page"><p className="loading">Loading report…</p></div>;
  if (error) return <div className="page"><p className="error">Error: {error}</p></div>;
  if (!report) return <div className="page"><p className="empty">Report not found.</p></div>;

  return (
    <div className="page">
      <h1 className="page-title">{report.event_meta.cluster_id}</h1>
      <p className="page-subtitle">{report.event_meta.search_query}</p>

      <Zone1 report={report} />
      <Zone2 report={report} />
      <Zone3 report={report} />
    </div>
  );
}
