import { useState, useEffect, useCallback } from "react";
import { Link } from "react-router-dom";
import type { ClusterSummary } from "../types";
import { fetchReports, deleteReport } from "../api";
import { PipelineRunner } from "./PipelineRunner";

type PipelineState = "idle" | "running" | "complete" | "error";

export function HomePage() {
	const [reports, setReports] = useState<ClusterSummary[]>([]);
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState<string | null>(null);
	const [pipelineState, setPipelineState] = useState<PipelineState>("idle");
	const [hasStoredResult, setHasStoredResult] = useState(false);

	const loadReports = useCallback(() => {
		setLoading(true);
		setError(null);
		fetchReports()
			.then(setReports)
			.catch((e: Error) => setError(e.message))
			.finally(() => setLoading(false));
	}, []);

	const handleDelete = useCallback(
		(e: React.MouseEvent, clusterId: string, query: string) => {
			e.preventDefault();
			e.stopPropagation();
			if (window.confirm(`Delete "${query}" report?`)) {
				deleteReport(clusterId).then(loadReports);
			}
		},
		[loadReports],
	);

	const handleStateChange = useCallback(
		(state: PipelineState, stored?: boolean) => {
			setPipelineState(state);
			if (stored !== undefined) {
				setHasStoredResult(stored);
			}
		},
		[],
	);

	useEffect(() => {
		loadReports();
	}, [loadReports]);

	const showEmptyState =
		!loading &&
		!error &&
		reports.length === 0 &&
		pipelineState === "idle" &&
		!hasStoredResult;

	return (
		<div className="page">
			<PipelineRunner
				onComplete={loadReports}
				onStateChange={handleStateChange}
			/>

			{loading && <p className="loading">Loading reports…</p>}
			{error && <p className="error">Error: {error}</p>}
			{showEmptyState && (
				<p className="empty">No reports yet. Run a pipeline to get started.</p>
			)}
			{!loading && !error && reports.length > 0 && (
				<>
					<h1 className="page-title">Forensic Reports</h1>
					<div className="report-list">
						{reports.map((r) => (
							<Link
								key={r.cluster_id}
								to={`/event/${r.cluster_id}`}
								className="report-card"
							>
								<div className="report-card-body">
									<h2>{r.search_query}</h2>
									<p className="report-meta">
										{r.industry_vertical} · {r.corpus_count} articles ·{" "}
										{r.timestamp_utc}
									</p>
								</div>
								<button
									className="delete-btn"
									aria-label={`Delete ${r.search_query} report`}
									onClick={(e) => handleDelete(e, r.cluster_id, r.search_query)}
								>
									×
								</button>
							</Link>
						))}
					</div>
				</>
			)}
		</div>
	);
}
