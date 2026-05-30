import { useState, useRef } from "react";
import { useNavigate } from "react-router-dom";
import type { PipelineEvent, PipelineStep } from "../types";
import { streamPipeline } from "../api";

const VERTICALS = ["TECHNOLOGY", "FINANCE", "POLITICS", "HEALTH", "ENTERTAINMENT"];

const STEP_LABELS: Record<PipelineStep, string> = {
  discovering:  "Discovering articles",
  ingesting:    "Ingesting content",
  analyzing:    "Analyzing narratives",
  synthesizing: "Synthesizing report",
  complete:     "Complete",
  error:        "Error",
};

// Ordered so steps render top-to-bottom in arrival order (Map preserves insertion order).
type RunnerState = "idle" | "running" | "complete" | "error";

export function PipelineRunner({ onComplete }: { onComplete?: () => void }) {
  const [keyword, setKeyword]         = useState("");
  const [vertical, setVertical]       = useState("TECHNOLOGY");
  const [runnerState, setRunnerState] = useState<RunnerState>("idle");
  // Map<step, message> — last-write-wins per step, preserves insertion order for rendering
  const [stepMessages, setStepMessages] = useState<Map<PipelineStep, string>>(new Map());
  const [errorDetail, setErrorDetail] = useState<string | null>(null);
  const esRef                         = useRef<EventSource | null>(null);
  const navigate                      = useNavigate();

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!keyword.trim() || runnerState === "running") return;

    setStepMessages(new Map());
    setErrorDetail(null);
    setRunnerState("running");

    esRef.current = streamPipeline(
      keyword.trim(),
      vertical,
      (event: PipelineEvent) => {
        setStepMessages((prev) => new Map(prev).set(event.step, event.message));
        if (event.step === "complete") {
          esRef.current?.close();
          setRunnerState("complete");
          onComplete?.();
          if (event.cluster_id) navigate(`/event/${event.cluster_id}`);
        } else if (event.step === "error") {
          esRef.current?.close();
          setRunnerState("error");
          setErrorDetail(event.detail ?? event.message);
        }
      },
      (_err: Event) => {
        esRef.current?.close();
        setRunnerState("error");
        setErrorDetail("Connection to server lost.");
      },
    );
  };

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
          {VERTICALS.map((v) => <option key={v} value={v}>{v}</option>)}
        </select>
        <button
          type="submit"
          className="pipeline-submit-btn"
          disabled={runnerState === "running" || !keyword.trim()}
        >
          {runnerState === "running" ? "Running…" : "Run Pipeline"}
        </button>
      </form>

      {stepMessages.size > 0 && (
        <div className="pipeline-progress" role="status" aria-live="polite">
          {Array.from(stepMessages.entries()).map(([step, message]) => (
            <div key={step} className={`pipeline-step pipeline-step--${step}`}>
              <span className="step-label">{STEP_LABELS[step] ?? step}</span>
              <span className="step-message">{message}</span>
            </div>
          ))}
        </div>
      )}

      {runnerState === "error" && errorDetail && (
        <p className="pipeline-error">Pipeline failed: {errorDetail}</p>
      )}
    </div>
  );
}
