import { useState, useRef, useEffect, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import type {
	PipelineEvent,
	PipelineStep,
	ArticleProgress,
	ArticleStatus,
} from "../types";
import { streamPipeline } from "../api";

const VERTICALS = [
	"TECHNOLOGY",
	"FINANCE",
	"POLITICS",
	"HEALTH",
	"ENTERTAINMENT",
];

const STEP_LABELS: Record<PipelineStep, string> = {
	discovering: "Discovering articles",
	ingesting: "Ingesting content",
	analyzing: "Analyzing narratives",
	synthesizing: "Synthesizing report",
	complete: "Complete",
	error: "Error",
};

type RunnerState = "idle" | "running" | "complete" | "error";

const STATUS_BADGE: Record<ArticleStatus, { label: string; cls: string }> = {
	ok: { label: "✅", cls: "article-ok" },
	failed: { label: "❌", cls: "article-failed" },
	rejected: { label: "⛔", cls: "article-rejected" },
	skipped: { label: "⏭️", cls: "article-skipped" },
};

const STORAGE_KEY = "narrative_alpha_pipeline_result";

interface PipelineStorageEntry {
	cluster_id: string;
	search_query: string;
	status: "complete" | "error";
	error_detail?: string;
}

export function PipelineRunner({
	onComplete,
	onStateChange,
}: {
	onComplete?: () => void;
	onStateChange?: (state: RunnerState, hasStoredResult?: boolean) => void;
}) {
	const [keyword, setKeyword] = useState("");
	const [vertical, setVertical] = useState("TECHNOLOGY");
	const [runnerState, setRunnerState] = useState<RunnerState>("idle");
	const [phaseStatus, setPhaseStatus] = useState<
		Record<string, "active" | "complete">
	>({});
	const [discoverySummary, setDiscoverySummary] = useState<string | null>(null);
	const [phaseMessage, setPhaseMessage] = useState<Record<string, string>>({});
	const [ingestedArticles, setIngestedArticles] = useState<ArticleProgress[]>(
		[],
	);
	const [errorDetail, setErrorDetail] = useState<string | null>(null);
	const esRef = useRef<EventSource | null>(null);
	const navigate = useNavigate();

	// Read sessionStorage for prior run result
	const [storedResult, setStoredResult] = useState<PipelineStorageEntry | null>(
		() => {
			try {
				const raw = sessionStorage.getItem(STORAGE_KEY);
				return raw ? (JSON.parse(raw) as PipelineStorageEntry) : null;
			} catch {
				return null;
			}
		},
	);

	const clearStoredResult = useCallback(() => {
		sessionStorage.removeItem(STORAGE_KEY);
		setStoredResult(null);
	}, []);

	// Close EventSource on unmount
	useEffect(() => {
		return () => {
			esRef.current?.close();
		};
	}, []);

	// Notify parent of stored result so empty-state is hidden
	useEffect(() => {
		if (storedResult && runnerState === "idle") {
			onStateChange?.("idle", true);
		}
	}, [storedResult, runnerState, onStateChange]);

	const handleSubmit = (e: React.FormEvent) => {
		e.preventDefault();
		if (!keyword.trim() || runnerState === "running") return;

		setPhaseStatus({});
		setDiscoverySummary(null);
		setIngestedArticles([]);
		setErrorDetail(null);
		setRunnerState("running");
		onStateChange?.("running");
		setStoredResult(null); // hide banner during new run, keep sessionStorage

		esRef.current = streamPipeline(
			keyword.trim(),
			vertical,
			(event: PipelineEvent) => {
				// Track phase active/completed
				if (
					event.step === "discovering" ||
					event.step === "ingesting" ||
					event.step === "analyzing" ||
					event.step === "synthesizing"
				) {
					setPhaseStatus((prev) => {
						const detail = event.detail;
						const isComplete =
							detail &&
							typeof detail === "object" &&
							"status" in detail &&
							detail.status === "complete";
						if (isComplete) {
							return { ...prev, [event.step]: "complete" };
						}
						if (!prev[event.step]) {
							return { ...prev, [event.step]: "active" };
						}
						return prev;
					});

					// Track phase message for dynamic display
					if (event.message) {
						setPhaseMessage((prev) => ({
							...prev,
							[event.step]: event.message,
						}));
					}
				}

				// Capture discovery summary
				if (
					event.step === "discovering" &&
					event.detail &&
					typeof event.detail === "object" &&
					"status" in event.detail &&
					event.detail.status === "complete"
				) {
					setDiscoverySummary(event.message);
				}

				// Accumulate per-article ingest results
				if (
					event.step === "ingesting" &&
					event.detail &&
					typeof event.detail === "object" &&
					"status" in event.detail &&
					event.detail.status !== "complete"
				) {
					const prog = event.detail as unknown as ArticleProgress;
					if (prog.source_name || prog.domain) {
						setIngestedArticles((prev) => [...prev, prog]);
					}
				}

				if (event.step === "complete") {
					esRef.current?.close();
					setRunnerState("complete");
					onStateChange?.("complete");
					setPhaseStatus((prev) => ({ ...prev, complete: "complete" }));
					onComplete?.();
					// Save to sessionStorage for cross-route persistence
					if (event.cluster_id) {
						sessionStorage.setItem(
							STORAGE_KEY,
							JSON.stringify({
								cluster_id: event.cluster_id,
								search_query: keyword.trim(),
								status: "complete",
							} as PipelineStorageEntry),
						);
						navigate(`/event/${event.cluster_id}`);
					}
				} else if (event.step === "error") {
					esRef.current?.close();
					setRunnerState("error");
					onStateChange?.("error");
					const errMsg =
						typeof event.detail === "string" ? event.detail : event.message;
					setErrorDetail(errMsg);
					sessionStorage.setItem(
						STORAGE_KEY,
						JSON.stringify({
							cluster_id: "",
							search_query: keyword.trim(),
							status: "error",
							error_detail: errMsg,
						} as PipelineStorageEntry),
					);
				}
			},
			(_err: Event) => {
				esRef.current?.close();
				setRunnerState("error");
				onStateChange?.("error");
				const errMsg = "Connection to server lost.";
				setErrorDetail(errMsg);
				sessionStorage.setItem(
					STORAGE_KEY,
					JSON.stringify({
						cluster_id: "",
						search_query: keyword.trim(),
						status: "error",
						error_detail: errMsg,
					} as PipelineStorageEntry),
				);
			},
		);
	};

	const phaseOrder: PipelineStep[] = [
		"discovering",
		"ingesting",
		"analyzing",
		"synthesizing",
	];

	return (
		<div className="pipeline-runner">
			<form className="pipeline-form" onSubmit={handleSubmit}>
				<input
					className="pipeline-keyword-input"
					type="text"
					placeholder="Enter keyword (e.g. AI regulation)"
					value={keyword}
					onChange={(e) => setKeyword(e.target.value)}
					disabled={runnerState === "running"}
					required
				/>
				<select
					className="pipeline-vertical-select"
					value={vertical}
					onChange={(e) => setVertical(e.target.value)}
					disabled={runnerState === "running"}
				>
					{VERTICALS.map((v) => (
						<option key={v} value={v}>
							{v}
						</option>
					))}
				</select>
				<button
					type="submit"
					className="pipeline-submit-btn"
					disabled={runnerState === "running" || !keyword.trim()}
				>
					{runnerState === "running" ? "Running…" : "Run Pipeline"}
				</button>
			</form>

			{/* Stored result banner (from sessionStorage) */}
			{storedResult && runnerState === "idle" && (
				<div
					className={`stored-result-banner stored-result-banner--${storedResult.status}`}
				>
					{storedResult.status === "complete" ? (
						<span>
							Report ready —{" "}
							<a
								href={`/event/${storedResult.cluster_id}`}
								onClick={(e) => {
									e.preventDefault();
									navigate(`/event/${storedResult.cluster_id}`);
								}}
							>
								{storedResult.search_query}
							</a>
						</span>
					) : (
						<span>
							Pipeline failed for "{storedResult.search_query}":{" "}
							{storedResult.error_detail}
						</span>
					)}
					<button className="stored-result-dismiss" onClick={clearStoredResult}>
						✕
					</button>
				</div>
			)}

			{/* Running / progress UI */}
			{(runnerState !== "idle" || Object.keys(phaseStatus).length > 0) && (
				<div className="pipeline-progress" role="status" aria-live="polite">
					{phaseOrder.map((step) => {
						const status = phaseStatus[step];
						if (!status) return null;
						const isComplete = status === "complete";
						const label = STEP_LABELS[step] ?? step;

						return (
							<div
								key={step}
								className={`pipeline-step pipeline-step--${step} ${isComplete ? "pipeline-step--done" : ""}`}
							>
								{isComplete ? (
									<span className="phase-indicator phase-indicator--done">
										✓
									</span>
								) : (
									<span className="phase-indicator phase-indicator--active">
										⟳
									</span>
								)}
								<span className="step-label">{label}</span>
								{step === "discovering" && discoverySummary && (
									<span className="step-message">{discoverySummary}</span>
								)}
								{step === "ingesting" && (
									<span className="step-message">
										{ingestedArticles.length > 0
											? `Processed ${ingestedArticles.length} article${ingestedArticles.length !== 1 ? "s" : ""}`
											: "Fetching..."}
									</span>
								)}
								{step === "analyzing" && !isComplete && (
									<span className="step-message">
										{phaseMessage["analyzing"] ||
											"Running entity and graph analysis..."}
									</span>
								)}
								{step === "synthesizing" && !isComplete && (
									<span className="step-message">
										{phaseMessage["synthesizing"] ||
											"Generating forensic report..."}
									</span>
								)}
							</div>
						);
					})}

					{/* Ingested article list */}
					{ingestedArticles.length > 0 && (
						<div className="ingest-list">
							{ingestedArticles.map((a, i) => {
								const badge = STATUS_BADGE[a.status] ?? STATUS_BADGE.rejected;
								return (
									<div
										key={`${a.domain}-${i}`}
										className={`ingest-item ${badge.cls}`}
									>
										<span className="ingest-badge">{badge.label}</span>
										<span className="ingest-source">
											{a.source_name || a.domain}
										</span>
										{a.title && <span className="ingest-title">{a.title}</span>}
										<span className="ingest-domain">{a.domain}</span>
										<span className="ingest-status">{a.status}</span>
									</div>
								);
							})}
						</div>
					)}

					{/* Complete state */}
					{runnerState === "complete" && (
						<div className="pipeline-step pipeline-step--complete pipeline-step--done">
							<span className="phase-indicator phase-indicator--done">✓</span>
							<span className="step-label">Complete</span>
						</div>
					)}
				</div>
			)}

			{runnerState === "error" && errorDetail && (
				<p className="pipeline-error">Pipeline failed: {errorDetail}</p>
			)}
		</div>
	);
}
